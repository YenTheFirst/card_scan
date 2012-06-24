from elixir import metadata, Entity, Field, Integer, UnicodeText, using_options, BLOB

metadata.bind = "sqlite:///inventory.sqlite3"

class InvCard(Entity):
	name = Field(UnicodeText)
	set_name = Field(UnicodeText)
	box = Field(UnicodeText)
	scan_png = Field(BLOB)
	box_index = Field(Integer)
	status = Field(Integer)

	rowid = Field(Integer, primary_key=True)

	using_options(tablename='inv_cards')


	def __repr__(self):
		return "<%s/%s (%s/%d)>" % (self.set_name, self.name, self.box, self.box_index)

#class InvLog(Entity):
#	card_rowid

