CREATE TABLE lms_records (
	`id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	`email` TEXT NOT NULL,
	`student_data` TEXT,
    `programme_id` text DEFAULT NULL,
    `source_platform` text DEFAULT NULL,
	CHECK (`student_data` IS NULL OR JSON_VALID(`student_data`))
);