from elixir import session, setup_all, metadata
import sqlalchemy
from sqlalchemy import func
from models import InvCard
import re

setup_all(True)

def compress_smallest_box():
	last_box = session.query(func.max(sqlalchemy.cast(InvCard.box, sqlalchemy.Integer))).first()[0]
	box_capacity = list(metadata.bind.execute("select box,60 - count(*) as c from inv_cards where box not null group by box having c>0 order by c desc;"))
	if len(box_capacity) <= 0:
		raise Exception("there are no boxes in inventory to compress")
	remove_box = box_capacity[0][0]
	box_capacity = box_capacity[1:]

	cards_in_remove_box = InvCard.query.filter_by(box=str(remove_box)).order_by(InvCard.box_index.desc()).all()

	move_orders = fit_boxes(box_capacity, len(cards_in_remove_box))
	i=0

	print "********** move %d cards from box %s **********" % (60-box_capacity[0][1], remove_box)
	print "\tall boxes: %s" % sorted([int(x) for x in [remove_box] + [b for b,o in move_orders]])
	for box, count in move_orders:
		max_index = session.query(func.max(InvCard.box_index)).filter_by(box=box).one()[0]
		print "======= moving %d cards to box %s ======" % (count, box)
		for card in cards_in_remove_box[i:count+i]:
			print u"move %s to %s/%d" % (card, box, max_index)
			max_index += 1
			card.box = box
			card.box_index = max_index
		i+=count
	
	if remove_box != last_box:
		cards_in_last_box = InvCard.query.filter_by(box=str(last_box)).order_by(InvCard.box_index).all()
		print "********** finally, move all %d cards from %s to %s **********" % (len(cards_in_last_box),last_box, remove_box)
		for card in cards_in_last_box:
			card.box = remove_box
	raw_input()
	session.commit()


def fit_boxes(box_counts, num_cards):
	if num_cards == 0:
		return []

	largest = box_counts[0][1]
	if num_cards > largest:
		#if we're bigger than max, fill up max and continue
		return [box_counts[0]] + fit_boxes(box_counts[1:], num_cards - largest)
	else:
		#else, find the smallest box we fit in
		box = next(box for box, count in reversed(box_counts) if count >= num_cards)
		return [(box, num_cards)]
if __name__ == '__main__':
	compress_smallest_box()
