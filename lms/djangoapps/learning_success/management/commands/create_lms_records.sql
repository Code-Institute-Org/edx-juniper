CREATE TABLE lms_records (
    `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	`email` TEXT NOT NULL,
	`student_data` TEXT,
    `pathway` text DEFAULT NULL,
    `source_platform` text DEFAULT NULL,
	`state` VARCHAR(255) NOT NULL,
	CHECK (`student_data` IS NULL OR JSON_VALID(`student_data`))
);
