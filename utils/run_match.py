
import match_card
import cv
from models import InvCard
from elixir import setup_all, session
from sqlalchemy import distinct


if __name__ == '__main__':
	setup_all(True)

	sets = [s[0] for s in session.query(distinct(InvCard.set_name)).filter(InvCard.set_name != 'PROMO').all()]
	base_dir = u'/home/talin/Cockatrice/cards/downloadedPics'
	known = match_card.load_sets(base_dir, sets)
	cache = match_card.GradientCache(base_dir)
	print "all sets loaded!"

	cv.NamedWindow('debug')
	cv.StartWindowThread()
	match_card.match_db_cards(known, cache)
