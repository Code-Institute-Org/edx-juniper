CREATE TABLE lms_records (
    `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `email` TEXT NOT NULL,
    `student_data` TEXT,
    -- A pathway (temporary name; still to be agreed) is the grouping of
    -- multiple LMS programmes which amalgamated should represent the student's
    -- journey on that pathway (e.g. fullstack for disd and diwad)
    `pathway` text DEFAULT NULL,
    `source_platform` text DEFAULT NULL,
    -- current_programme is the current value of the CRM programme_id field
    `current_programme` text NOT NULL,
    `state` VARCHAR(255) NOT NULL,
    CHECK (`student_data` IS NULL OR JSON_VALID(`student_data`))
);
