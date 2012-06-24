from elixir import metadata, Entity, Field, using_options
from elixir import Integer, UnicodeText, BLOB, Enum, DateTime
from elixir import ManyToOne, OneToMany

metadata.bind = "sqlite:///inventory.sqlite3"

class InvCard(Entity):
	name = Field(UnicodeText)
	set_name = Field(UnicodeText)
	box = Field(UnicodeText)
	scan_png = Field(BLOB)
	box_index = Field(Integer)
	recognition_status = Field(Enum('scanned','candidate_match','incorrect_match','verified'))
	inv_logs = OneToMany('InvLog')

	rowid = Field(Integer, primary_key=True)

	using_options(tablename='inv_cards')


	def __repr__(self):
		return "<%s/%s (%s/%d)>" % (self.set_name, self.name, self.box, self.box_index)

class InvLog(Entity):
	card = ManyToOne('InvCard')
	direction = Field(Enum('added', 'removed'))
	reason = Field(UnicodeText)
	date = Field(DateTime)
	#I wish I had a ActiveRecord-like 'timestamps' here

	rowid = Field(Integer, primary_key = True)

	using_options(tablename='inv_logs')

	def __repr__(self):
		if self.direction == u'added':
			dir_text = 'added to'
		else:
			dir_text = 'removed_from'
		card_repr = "%s/%s(%d)" % (self.card.set_name, self.card.name, self.card.rowid)

		return "<%s: %s %s %s. \"%s\">" % (self.date, card_repr, dir_text, self.card.box, self.reason)

