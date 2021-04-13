CREATE TABLE lms_records (
    `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `email` TEXT NOT NULL,
    -- Initial data containing all programmes
    `partial_student_data` TEXT,
    -- Final data including combined programme based on current_programme
    -- and all other data from AMOS
    `final_student_data` TEXT,
    -- A pathway (temporary name; still to be agreed) is the grouping of
    -- multiple LMS programmes which amalgamated should represent the student's
    -- journey on that pathway (e.g. fullstack for disd and diwad)
    `pathway` text DEFAULT NULL,
    `source_platform` text DEFAULT NULL,
    -- current_programme is the current value of the CRM Programme_Id field
    `current_programme` text NULL,
    -- current_lms_version is the current value of the CRM LMS_Version field
    `current_lms_version` text NULL,
    `state` VARCHAR(255) NOT NULL,
    CHECK (`partial_student_data` IS NULL OR JSON_VALID(`partial_student_data`)),
    CHECK (`final_student_data` IS NULL OR JSON_VALID(`final_student_data`))
);
