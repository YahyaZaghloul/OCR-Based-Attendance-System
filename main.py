"""
Smart Door Authentication System - CSV-Based Configuration
-----------------------------------------------------------
A command-line simulated smart door system.
Authentication occurs in stages:
    OCR identity verification → voice passphrase → unlock

The system handles attempts, locks after repeated failures, and writes logs.
All configuration is loaded from CSV files.
"""

import cv2
import pytesseract
from PIL import Image
import speech_recognition as sr
from datetime import datetime
import os
import csv

# ============================================================================
# CSV FILE PATHS
# ============================================================================

USERS_CSV = "authorized_users.csv"      # User credentials database
CONFIG_CSV = "system_config.csv"        # System configuration
LOG_FILE = "door_logs.txt"              # Persistent log file

# Tesseract path (uncomment and set if needed on Windows)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# ============================================================================
# CSV FILE INITIALIZATION
# ============================================================================

def create_sample_csv_files():
    """
    Create sample CSV files if they don't exist.
    """
    # Create authorized_users.csv
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Username', 'ExpectedName', 'ExpectedID', 'VoicePassphrase', 'Role', 'Status'])
            writer.writerow(['admin_john', 'JOHN DOE', '12345', 'open sesame', 'Admin', 'Active'])
            writer.writerow(['admin_sarah', 'SARAH ADMIN', '11111', 'admin access', 'Admin', 'Active'])
            writer.writerow(['user_emma', 'EMMA WILSON', '67890', 'hello door', 'User', 'Active'])
            writer.writerow(['user_michael', 'MICHAEL CHEN', '54321', 'unlock now', 'User', 'Active'])
        print(f"✓ Created sample file: {USERS_CSV}")
    
    # Create system_config.csv
    if not os.path.exists(CONFIG_CSV):
        with open(CONFIG_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Setting', 'Value'])
            writer.writerow(['MaxFailedAttempts', '3'])
            writer.writerow(['LogFile', 'door_logs.txt'])
            writer.writerow(['OCRConfidenceThreshold', '60'])
        print(f"✓ Created sample file: {CONFIG_CSV}")


# ============================================================================
# CSV READING FUNCTIONS
# ============================================================================

def load_system_config():
    """
    Load system configuration from CSV file.
    
    Returns:
        Dictionary with configuration settings
    """
    config = {
        'MaxFailedAttempts': 3,
        'LogFile': 'door_logs.txt',
        'OCRConfidenceThreshold': 60
    }
    
    try:
        with open(CONFIG_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                setting = row['Setting']
                value = row['Value']
                
                # Convert numeric values
                if setting == 'MaxFailedAttempts' or setting == 'OCRConfidenceThreshold':
                    config[setting] = int(value)
                else:
                    config[setting] = value
        
        print(f"✓ System configuration loaded from {CONFIG_CSV}")
        return config
        
    except FileNotFoundError:
        print(f"⚠️  Config file not found, using defaults")
        return config
    except Exception as e:
        print(f"⚠️  Error loading config: {e}, using defaults")
        return config


def load_user_credentials(username):
    """
    Load user credentials from CSV file.
    
    Args:
        username: Username to look up
        
    Returns:
        Dictionary with user credentials or None if not found
    """
    try:
        with open(USERS_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Username'].lower() == username.lower():
                    if row['Status'].upper() != 'ACTIVE':
                        print(f"⚠️  User '{username}' status: {row['Status']}")
                        return None
                    
                    print(f"✓ User credentials loaded from {USERS_CSV}")
                    return {
                        'Username': row['Username'],
                        'ExpectedName': row['ExpectedName'],
                        'ExpectedID': row['ExpectedID'],
                        'VoicePassphrase': row['VoicePassphrase'],
                        'Status': row['Status']
                    }
        
        print(f"✗ User '{username}' not found in {USERS_CSV}")
        return None
        
    except FileNotFoundError:
        print(f"✗ ERROR: Users database file not found: {USERS_CSV}")
        print("Please create the file or run with sample data generation.")
        return None
    except Exception as e:
        print(f"✗ ERROR: Failed to load user credentials: {e}")
        return None


def list_authorized_users():
    """
    Display list of authorized users from CSV.
    """
    try:
        with open(USERS_CSV, 'r') as f:
            reader = csv.DictReader(f)
            users = list(reader)
            
            if not users:
                print("No users found in database.")
                return
            
            print("\n" + "="*60)
            print("AUTHORIZED USERS")
            print("="*60)
            for user in users:
                status_icon = "✓" if user['Status'].upper() == 'ACTIVE' else "✗"
                print(f"{status_icon} {user['Username']:20s} | {user['ExpectedName']:20s} | Status: {user['Status']}")
            print("="*60)
            
    except FileNotFoundError:
        print(f"✗ Users database file not found: {USERS_CSV}")
    except Exception as e:
        print(f"✗ Error reading users: {e}")


# ============================================================================
# 1. OCR IMAGE LOADING AND TEXT EXTRACTION
# ============================================================================

def load_and_extract_text(image_path):
    """
    Load ID image using PIL and extract text with pytesseract.
    
    Args:
        image_path: Path to the ID image file
        
    Returns:
        Extracted text string or None if error occurs
    """
    try:
        # Load image with PIL
        img = Image.open(image_path)
        print(f"✓ Image loaded successfully: {image_path}")
        
        # Extract text using pytesseract
        extracted_text = pytesseract.image_to_string(img)
        print(f"✓ OCR text extraction completed")
        
        return extracted_text
        
    except FileNotFoundError:
        print(f"✗ ERROR: Image file not found: {image_path}")
        return None
    except Exception as e:
        print(f"✗ ERROR: Failed to load or process image: {e}")
        return None


# ============================================================================
# 2. OCR PREPROCESSING (resize, grayscale, threshold)
# ============================================================================

def preprocess_image(image_path):
    """
    Apply preprocessing to improve OCR accuracy:
    - Resize image
    - Convert to grayscale
    - Apply threshold
    
    Args:
        image_path: Path to the ID image
        
    Returns:
        Preprocessed image or None if error occurs
    """
    try:
        # Read image with OpenCV
        img = cv2.imread(image_path)
        
        if img is None:
            print(f"✗ ERROR: Unable to read image with OpenCV")
            return None
        
        # STEP 1: Resize image (scale to improve OCR if too small/large)
        height, width = img.shape[:2]
        if width < 800:
            scale_factor = 800 / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            print(f"✓ Image resized to {new_width}x{new_height}")
        
        # STEP 2: Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        print(f"✓ Converted to grayscale")
        
        # STEP 3: Apply threshold (binary image for better OCR)
        # Using adaptive threshold for varying lighting conditions
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        print(f"✓ Threshold applied")
        
        # Convert to PIL Image for pytesseract
        preprocessed_img = Image.fromarray(thresh)
        
        return preprocessed_img
        
    except Exception as e:
        print(f"✗ ERROR: Preprocessing failed: {e}")
        return None


# ============================================================================
# 3. COMPARE OCR RESULT TO EXPECTED VALUE (FROM CSV)
# ============================================================================

def verify_identity(image_path, user_credentials):
    """
    Compare OCR result to expected student name or ID field from CSV.
    
    Args:
        image_path: Path to ID image
        user_credentials: Dictionary with user credentials from CSV
        
    Returns:
        True if identity verified, False otherwise
    """
    print("\n" + "="*60)
    print("STAGE 1: OCR IDENTITY VERIFICATION")
    print("="*60)
    
    expected_name = user_credentials['ExpectedName']
    expected_id = user_credentials['ExpectedID']
    
    # Preprocess image
    print("\nPreprocessing image...")
    preprocessed_img = preprocess_image(image_path)
    
    if preprocessed_img is None:
        print("✗ Preprocessing failed - cannot verify identity")
        return False
    
    # Extract text from preprocessed image
    print("\nExtracting text from ID...")
    try:
        extracted_text = pytesseract.image_to_string(preprocessed_img)
        
        if not extracted_text or extracted_text.strip() == "":
            print("✗ ERROR: No text could be extracted from image")
            return False
            
        print(f"✓ Text extracted successfully")
        print(f"\nExtracted text preview:")
        print("-" * 60)
        print(extracted_text[:200])  # Show first 200 chars
        print("-" * 60)
        
    except Exception as e:
        print(f"✗ ERROR: OCR extraction failed: {e}")
        return False
    
    # Compare extracted text with expected values from CSV
    print("\nVerifying identity...")
    print(f"Looking for: Name='{expected_name}' OR ID='{expected_id}'")
    
    extracted_upper = extracted_text.upper()
    
    # Check for expected name
    name_found = expected_name.upper() in extracted_upper
    # Check for expected ID
    id_found = expected_id in extracted_text
    
    if name_found:
        print(f"✓ Name match found: {expected_name}")
    if id_found:
        print(f"✓ ID match found: {expected_id}")
    
    # Identity verified if either name or ID is found
    if name_found or id_found:
        print("\n✓ IDENTITY VERIFIED")
        return True
    else:
        print(f"\n✗ IDENTITY VERIFICATION FAILED")
        return False


# ============================================================================
# 4. VOICE PASSPHRASE CAPTURE USING speech_recognition
# ============================================================================

def capture_voice_passphrase():
    """
    Use speech_recognition.Recognizer() to capture voice passphrase.
    
    Returns:
        Recognized text or None if error occurs
    """
    recognizer = sr.Recognizer()
    
    try:
        # Use microphone as source
        with sr.Microphone() as source:
            print("\n🎤 Listening... Please speak your passphrase")
            
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Listen for audio
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            print("✓ Audio captured, processing...")
            
            # Recognize speech using Google Speech Recognition
            text = recognizer.recognize_google(audio)
            
            return text.lower().strip()
            
    except sr.WaitTimeoutError:
        print("✗ ERROR: No speech detected (timeout)")
        return None
    except sr.UnknownValueError:
        print("✗ ERROR: Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"✗ ERROR: Speech recognition service error: {e}")
        return None
    except OSError:
        print("✗ ERROR: Microphone not found or not accessible")
        return None
    except Exception as e:
        print(f"✗ ERROR: Voice capture failed: {e}")
        return None


def verify_voice(user_credentials):
    """
    Verify voice passphrase matches expected value from CSV.
    
    Args:
        user_credentials: Dictionary with user credentials from CSV
        
    Returns:
        True if passphrase correct, False otherwise
    """
    print("\n" + "="*60)
    print("STAGE 2: VOICE PASSPHRASE VERIFICATION")
    print("="*60)
    
    expected_passphrase = user_credentials['VoicePassphrase']
    print(f"   (Expected passphrase: '{expected_passphrase}')")
    
    recognized_text = capture_voice_passphrase()
    
    if recognized_text is None:
        print("\n✗ VOICE VERIFICATION FAILED (capture error)")
        return False
    
    print(f"\nRecognized: '{recognized_text}'")
    
    # Compare with expected passphrase (case-insensitive)
    if recognized_text == expected_passphrase.lower():
        print("✓ VOICE PASSPHRASE VERIFIED")
        return True
    else:
        print(f"✗ VOICE VERIFICATION FAILED")
        print(f"Expected: '{expected_passphrase}'")
        return False


# ============================================================================
# 5. CLEAR MULTI-STAGE FLOW (OCR -> Voice)
# ============================================================================

def authenticate_user(image_path, user_credentials, config):
    """
    Clear multi-stage authentication flow:
    Stage 1: OCR identity verification
    Stage 2: Voice passphrase verification
    
    Args:
        image_path: Path to ID image
        user_credentials: User credentials from CSV
        config: System configuration from CSV
        
    Returns:
        True if both stages pass, False otherwise
    """
    username = user_credentials['Username']
    
    print("\n" + "="*60)
    print("🚪 SMART DOOR AUTHENTICATION SYSTEM")
    print("="*60)
    print(f"User: {username}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # STAGE 1: OCR Identity Verification
    stage1_passed = verify_identity(image_path, user_credentials)
    
    if not stage1_passed:
        log_attempt(username, "OCR", "FAILED", config)
        return False
    
    log_attempt(username, "OCR", "PASSED", config)
    
    # STAGE 2: Voice Passphrase Verification
    stage2_passed = verify_voice(user_credentials)
    
    if not stage2_passed:
        log_attempt(username, "VOICE", "FAILED", config)
        return False
    
    log_attempt(username, "VOICE", "PASSED", config)
    
    # Both stages passed
    print("\n" + "="*60)
    print("✓✓✓ AUTHENTICATION SUCCESSFUL - DOOR UNLOCKED ✓✓✓")
    print("="*60)
    log_attempt(username, "UNLOCK", "SUCCESS", config)
    
    return True


# ============================================================================
# 6. ATTEMPT LIMIT - LOCK AFTER FAILED ATTEMPTS (FROM CSV CONFIG)
# ============================================================================

def count_recent_failures(username, config):
    """
    Count failed attempts for a user from log file.
    
    Args:
        username: Username to check
        config: System configuration
        
    Returns:
        Number of recent failed attempts
    """
    log_file = config['LogFile']
    
    if not os.path.exists(log_file):
        return 0
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Count failures since last success
        failure_count = 0
        for line in reversed(lines):
            if username in line:
                if "FAILED" in line:
                    failure_count += 1
                elif "SUCCESS" in line:
                    # Reset count after successful unlock
                    break
        
        return failure_count
        
    except Exception as e:
        print(f"Warning: Could not read log file: {e}")
        return 0


def is_locked(username, config):
    """
    Check if user is locked out due to failed attempts.
    Uses MaxFailedAttempts from CSV config.
    
    Args:
        username: Username to check
        config: System configuration from CSV
        
    Returns:
        True if locked, False otherwise
    """
    failures = count_recent_failures(username, config)
    max_attempts = config['MaxFailedAttempts']
    return failures >= max_attempts


# ============================================================================
# 7. PERSISTENT LOG FILE (path from CSV)
# ============================================================================

def log_attempt(username, stage, result, config):
    """
    Write log entry with timestamp, user, stage, and result.
    Log file path is read from CSV configuration.
    
    Args:
        username: Username attempting access
        stage: Authentication stage (OCR, VOICE, UNLOCK)
        result: Result (PASSED, FAILED, SUCCESS)
        config: System configuration
    """
    log_file = config['LogFile']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] User: {username:15s} | Stage: {stage:10s} | Result: {result}\n"
    
    try:
        with open(log_file, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")


# ============================================================================
# 8. GRACEFUL ERROR HANDLING
# ============================================================================

def main():
    """
    Main entry point with graceful error handling.
    All configuration loaded from CSV files.
    """
    print("\n" + "="*60)
    print("🚪 SMART DOOR SYSTEM - STARTUP")
    print("="*60)
    
    # Create sample CSV files if they don't exist
    create_sample_csv_files()
    
    # Load system configuration from CSV
    print("\nLoading system configuration...")
    config = load_system_config()
    print(f"   Max Failed Attempts: {config['MaxFailedAttempts']}")
    print(f"   Log File: {config['LogFile']}")
    
    # Display authorized users
    list_authorized_users()
    
    # Get username
    username = input("\nEnter your username: ").strip()
    if not username:
        print("✗ ERROR: Username required")
        return
    
    # Load user credentials from CSV
    print(f"\nLoading credentials for '{username}'...")
    user_credentials = load_user_credentials(username)
    
    if user_credentials is None:
        print("✗ ERROR: User not authorized or credentials not found")
        log_attempt(username, "SYSTEM", "UNAUTHORIZED", config)
        return
    
    # Check if user is locked out
    if is_locked(username, config):
        failures = count_recent_failures(username, config)
        max_attempts = config['MaxFailedAttempts']
        print("\n" + "="*60)
        print("🔒 SYSTEM LOCKED")
        print("="*60)
        print(f"User '{username}' has exceeded maximum failed attempts ({failures}/{max_attempts})")
        print("Access denied. Please contact administrator.")
        print("="*60)
        log_attempt(username, "SYSTEM", "LOCKED_OUT", config)
        return
    
    # Get ID image path
    image_path = input("\nEnter path to ID image: ").strip()
    
    if not image_path:
        print("✗ ERROR: No image path provided")
        return
    
    if not os.path.exists(image_path):
        print(f"✗ ERROR: File not found: {image_path}")
        log_attempt(username, "SYSTEM", "FILE_NOT_FOUND", config)
        return
    
    # Attempt authentication
    try:
        success = authenticate_user(image_path, user_credentials, config)
        
        if not success:
            failures = count_recent_failures(username, config)
            max_attempts = config['MaxFailedAttempts']
            remaining = max_attempts - failures
            
            print(f"\n⚠️  Failed attempts: {failures}/{max_attempts}")
            
            if remaining > 0:
                print(f"⚠️  Remaining attempts: {remaining}")
            else:
                print("🔒 ACCOUNT LOCKED - Maximum attempts exceeded")
                
    except KeyboardInterrupt:
        print("\n\n✗ Authentication cancelled by user")
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}")
        log_attempt(username, "SYSTEM", f"ERROR: {str(e)}", config)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()