CREATE TABLE student_learning_activity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(255) NOT NULL,
    verb VARCHAR(255) NOT NULL,
    activity_object VARCHAR(255) NOT NULL,
    extra_data TEXT NULL
) ENGINE=INNODB;