import re

def calculate_cmc(manacost):
	#stub
	return 0

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

class SearchCard:
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
		if set(new_card.sets).intersection(set(["UNH","UG"])): #don't even try for these
			del new_card
			return None

		set_attribute("colors", "color", required = False, multiple = True)
		set_attribute("manacost")
		new_card.cmc = calculate_cmc(new_card.manacost)
		#just simple types for now, not split into super/basic/subtypes
		set_attribute("types", "type", pre_process =
				lambda type_line: type_line.replace("-",'').split())

		if "Creature" in new_card.types:
			#power or toughness can be an integer, '*', or {fraction}
			#well, the last one's only for Little Girl ;)
			p_t = re.findall('\d+|\*',"*/*")
			new_card.power, new_card.toughness = map(maybe_to_int, p_t)

		if "Planeswalker" in new_card.types:
			set_attribute("loyalty")

		set_attribute("text")

		return new_card

	def __repr__(self):
		return "<%s: %s>" % (self.__class__, self.name)

#load all cards with
#cards = filter(None, (search_card.SearchCard.from_xml_node(n) for n in root.findall("./cards/card")))
