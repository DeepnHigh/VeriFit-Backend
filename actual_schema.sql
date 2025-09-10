CREATE TABLE users (
	id INTEGER NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	user_type VARCHAR NOT NULL, 
	is_active BOOLEAN, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);
CREATE TABLE applicants (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	bio TEXT, 
	phone VARCHAR, 
	address VARCHAR, 
	education VARCHAR, 
	experience TEXT, 
	skills TEXT, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_applicants_id ON applicants (id);
