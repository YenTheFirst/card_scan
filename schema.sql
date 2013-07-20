create table inv_cards (
	name VARCHAR(255),
	set_name VARCHAR(255),
	scan_png BLOB,
	box INT,
	box_index INT,
	recognition_status VARCHAR(255),
	inventory_status VARCHAR(255)
);
