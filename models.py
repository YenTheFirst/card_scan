"""
copyright 2013-2014 Talin Salway

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from elixir import metadata, Entity, Field, using_options
from elixir import Integer, UnicodeText, BLOB, Enum, DateTime, Boolean
from elixir import ManyToOne, OneToMany, OneToOne
import sys
import config

metadata.bind = "sqlite:///%s" % (config.db_file)

class InvCard(Entity):
	name = Field(UnicodeText, index=True)
	set_name = Field(UnicodeText)
	box = Field(UnicodeText)
	scan_png = Field(BLOB)
	box_index = Field(Integer)
	recognition_status = Field(Enum('scanned','candidate_match','incorrect_match','verified'))
	inventory_status = Field(Enum('present', 'temporarily_out', 'permanently_gone'), index=True)
	is_foil = Field(Boolean, default=False)
	language = Field(UnicodeText, default=u'english')
	condition = Field(Enum('mint','near_mint', 'good', 'heavy_play'))

	inv_logs = OneToMany('InvLog')
	fix_log = OneToOne('FixLog')

	rowid = Field(Integer, primary_key=True)

	using_options(tablename='inv_cards')

	def most_recent_log(self):
		return sorted(self.inv_logs, key = lambda x: x.date)[-1]

	def __unicode__(self):
		return "<%s/%s (%s/%s)>" % (self.set_name, self.name, self.box, self.box_index)
	
	def __str__(self):
		return unicode(self).encode(sys.stdout.encoding)

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

class FixLog(Entity):
	card = ManyToOne('InvCard')
	orig_set = Field(UnicodeText)
	orig_name = Field(UnicodeText)
	new_set = Field(UnicodeText)
	new_name = Field(UnicodeText)
	scan_png = Field(BLOB)

	rowid = Field(Integer, primary_key = True)

	using_options(tablename='fix_log')

	def __repr__(self):
		return "<card %d was corrected from %s/%s to %s/%s>" % (self.card.rowid, self.orig_set, self.orig_name, self.new_set, self.new_name)
