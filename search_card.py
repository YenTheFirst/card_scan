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

import re
from models import InvCard

def calculate_cmc(manacost):
	components = re.findall("\([^()]+\)|\d+|[RGUWB]", manacost)
	total = 0
	for c in components:
		if re.match("^\d+$", c):
			total += int(c)
		elif re.match("^\(2/[RGUWB]\)$", c):
			total += 2
		else:
			total += 1
	return total

def maybe_to_int(string):
	try:
		return int(string)
	except ValueError: #not a valid int
		return string

def default_empty(val):
	if val is None:
		return ""
	else:
		return val

class Query:
	def __init__(self, requirement,
			children=None, field=None, value=None):
		self.requirement = requirement
		self.children = children
		self.field = field
		self.value = value
	
	def matches_card(self,card):
		if self.requirement == "AND":
			return all(c.matches_card(card) for c in self.children)
		elif self.requirement == "OR":
			return any(c.matches_card(card) for c in self.children)
		elif self.requirement == "NOT":
			return not self.children.matches_card(card)
		else:
			#it's attribute based. get the attribute
			try:
				attr = getattr(card, self.field)
			except AttributeError:
				#if we don't have the field, we can't be anything in comparison to it
				return False
			field_type = card.get_field_type(self.field)
			val = self.value

			comparisons = ["<", "=", ">"]
			if self.requirement in comparisons:
				#if it's a numerical field, attempt a numerical conversion
				if field_type == "num":
					try:
						val = int(val)
					except ValueError:
						pass
				return cmp(attr, val) == comparisons.index(self.requirement) - 1
			elif self.requirement == "=~":
				return re.search(val, attr)
			elif self.requirement == "HAS":
				return val in attr
	
	def __repr__(self):
		s = "%s(requirement = %r" % (self.__class__, self.requirement)
		for f in ["children", "field", "value"]:
			v = getattr(self, f)
			if v:
				s += ", %s = %r" % (f, v)
		s += ")"
		return s

	@classmethod
	def parse(cls, text):
		#turn text into a nice array of token-things
		tokens = re.findall(r"""
			#single quote strings
			'(?:\\'|[^'])*' |
			#double quote strings
			"(?:\\"|[^"])*" |
			#raw words
			\w+ |
			#parens
			[()] |
			#not
			! |
			#or comparison things
			[=<>~]+
		""", text, re.X)

		#nest on parentheses
		open_index = []
		def next_paren(tokens, start=0):
			indexes=[]
			for c in ['(',')']:
				try:
					indexes.append(tokens.index(c,start))
				except ValueError:
					indexes.append(len(tokens))
			return min(indexes)

		i = next_paren(tokens)
		while i < len(tokens):
			t = tokens[i]
			if t == '(':
				#open a paren on this i
				open_index.append(i)
			elif t == ')':
				#close. fold up between this i and our last open index
				open_i = open_index.pop()
				tokens[open_i:i+1] = [tokens[open_i+1:i]]
				i = open_i
			i = next_paren(tokens, i+1)

		if len(open_index) > 0:
			raise Exception("extra open paren at %d" % open_index[-1])

		def query_from_tokens(tokens):
			#first, bind all top-level logic.
			#NOT binds most closely, followed by AND and OR
			for logic in ["OR", "AND"]:
				top_logic = [i for i,t in enumerate(tokens) if str(t).upper() == logic]

				if len(top_logic) > 0:
					start = [0]+[t+1 for t in top_logic]
					end = top_logic+[len(tokens)]
					children = [query_from_tokens(tokens[s:e]) for s,e in zip(start, end)]
					return cls(requirement=logic, children = children)
			#check for NOT
			if str(tokens[0]).upper() in ["NOT", "!"]:
				child = query_from_tokens(tokens[1:])
				return cls(requirement="NOT", children = child)

			#if we're a bare nested statement, return us
			if len(tokens) == 1 and isinstance(tokens[0], list):
				return query_from_tokens(tokens[0])

			#otherwise, we should be 3 or more fields, with format:
			#<attr> <op> <values>
			if len(tokens) < 3:
				raise Exception("invalid expression: %s" % tokens)
			#attr should be a word
			attr = tokens[0]
			if not re.match(r'^\w+$',attr):
				raise Exception("invalid attribute: %s" % attr)

			#figure out the op
			negate = False
			while tokens[1].upper() in ["!", "NOT"]:
				negate = not negate
				#! could be short for 'is not', or we could have 'not has', etc.
				#if we have 4 or more tokens, delete this one
				if len(tokens) > 3:
					del tokens[1]
			op = tokens[1].upper()
			#do >= <= as negations
			if op == '>=':
				op = '<'
				negate = not negate
			if op == '<=':
				op = '>'
				negate = not negate
			if op == 'IS':
				op = '='
				if tokens[2].upper() == "NOT":
					del tokens[2]
					negate = not negate

			#if any of our values (tokens 2+) are enclosed in quotes, de-enclose them
			for i, t in enumerate(tokens[2:]):
				for quote in ["'",'"']:
					pattern = "^%s.*%s$" % (quote,quote)
					if re.match(pattern, t):
						tokens[i+2] = t.replace("\\%s" % quote, quote)[1:-1]

			print tokens
			full_q = cls(requirement=op, field=attr, value=tokens[2])
			if negate:
				full_q = cls(requirement="NOT", children = full_q)
			return full_q

			#else, we're just a simple match
			return cls(requirement=op, field=attr, value=tokens[2])
	
		return query_from_tokens(tokens)



class SearchCard:
	FIELD_TYPES = {
		"name": "str",
		"sets": "set",
		"formats": "set",
		"colors": "set",
		"manacost": "str",
		"cmc": "num",
		"types": "set",
		"power": "num",
		"toughness": "num",
		"loyalty": "num",
		"text": "str",
		"num_in_inventory": "num"
	}
	FORMATS = {
		"STANDARD": set(["M14", "DGM", "GTC", "RTR", "THS", "BNG"])
	}

	def get_field_type(self, field):
		return self.__class__.FIELD_TYPES[field]

	def inventory_card_query(self):
		return InvCard.query.filter_by(name=self.name).filter(InvCard.inventory_status.op('!=')('permanently_gone'))

	@property
	def num_in_inventory(self):
		return self.inventory_card_query().count()

	@classmethod
	def from_xml_node(cls, node):
		#this is for debug
		new_card = cls()
		outer = {"new_card": new_card}

		def set_attribute(attribute, field_name=None,
				required=True, multiple=False, pre_process=None):
			#default field_name
			if field_name is None:
				field_name = attribute

			values = [sub.text for sub in node.findall(field_name)]

			if len(values) == 0 and required:
				raise Exception("%s is required " % field_name)

			if not multiple:
				values = values[0]

			if pre_process:
				values = pre_process(values)

			setattr(outer["new_card"], attribute, default_empty(values))

		set_attribute("name")
		print "looking at ", new_card.name
		set_attribute("sets", "set", multiple = True)
		if set(new_card.sets).intersection(set(["Unhinged", "Unglued", "UNH","UH","UG", "UGL"])): #don't even try for these
			del new_card
			return None

		#set the formats
		new_card.formats = [format for format, sets
			in cls.FORMATS.iteritems()
			if sets.intersection(new_card.sets)]

		set_attribute("colors", "color", required = False, multiple = True)
		set_attribute("manacost")
		new_card.cmc = calculate_cmc(new_card.manacost)
		#just simple types for now, not split into super/basic/subtypes
		set_attribute("types", "type", pre_process =
				lambda type_line: type_line.replace("-",'').split())

		if "Creature" in new_card.types:
			#power or toughness can be an integer, '*', or {fraction}
			#well, the last one's only for Little Girl ;)
			p_t = node.find('pt').text.split('/')
			new_card.power, new_card.toughness = map(maybe_to_int, p_t)

		if "Planeswalker" in new_card.types:
			set_attribute("loyalty")

		set_attribute("text")

		return new_card

	def __repr__(self):
		return "<%s: %s>" % (self.__class__, self.name)







#load all cards with
#cards = filter(None, (search_card.SearchCard.from_xml_node(n) for n in root.findall("./cards/card")))
