################## TYPES OF ENROLLMENT ##################

# Define the different types of enrollment
ENROLLMENT_TYPES__ENROLLMENT = 0
ENROLLMENT_TYPES__UNENROLLMENT = 1
ENROLLMENT_TYPES__REENROLLMENT = 2
ENROLLMENT_TYPES__UPGRADE = 3

# Map the above types a more humanised version
ENROLLMENT_TYPES = (
    (ENROLLMENT_TYPES__ENROLLMENT, "Enrollment"),
    (ENROLLMENT_TYPES__UNENROLLMENT, "Un-enrollment"),
    (ENROLLMENT_TYPES__REENROLLMENT, "Re-enrollment"),
    (ENROLLMENT_TYPES__UPGRADE, "Upgrade")
)

################## ENROLLMENT EMAILS ##################

# Define the subject and template file name for each type of enrollment
ENROLLMENT_EMAIL__SUBJECT = "You have been enrolled in your Code Institute {} program"
ENROLLMENT_EMAIL__TEMPLATE_FILE = "enrollment_email.html"

UNENROLLMENT_EMAIL__SUBJECT = "Code Institute Unenrollment"
UNENROLLMENT_EMAIL__TEMPLATE_FILE = "unenrollment_email.html"

REENROLLMENT_EMAIL__SUBJECT = "You have been re-enrolled!"
REENROLLMENT_EMAIL__TEMPLATE_FILE = "reenrollment_email.html"

UPGRADE_EMAIL__SUBJECT = "You have been enrolled in your Code Institute {} program"
UPGRADE_EMAIL__TEMPLATE_FILE = "upgrade_enrollment_email.html"

# Combine the enrollment types with the email subjects and template files
ENROLLMENT_TEMPLATE_PARTS = {
    "ENROLLMENT_TYPE__ENROLLMENT": {
        "subject_template": ENROLLMENT_EMAIL__SUBJECT,
        "template_file": ENROLLMENT_EMAIL__TEMPLATE_FILE,
    },
    "ENROLLMENT_TYPE__UNENROLLMENT": {
        "subject_template": UNENROLLMENT_EMAIL__SUBJECT,
        "template_file": UNENROLLMENT_EMAIL__TEMPLATE_FILE,
    },
    "ENROLLMENT_TYPE__REENROLLMENT": {
        "subject_template": REENROLLMENT_EMAIL__SUBJECT,
        "template_file": REENROLLMENT_EMAIL__TEMPLATE_FILE,
    },
    "ENROLLMENT_TYPE__UPGRADE": {
        "subject_template": UPGRADE_EMAIL__SUBJECT,
        "template_file": UPGRADE_EMAIL__TEMPLATE_FILE,
    }
}