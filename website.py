# -*- coding: utf-8 -*-
from flask import Flask, send_file, safe_join, render_template, request
import sqlite3
from StringIO import StringIO
import os
import cv
from itertools import groupby
import re
from datetime import datetime
from operator import attrgetter
import urllib2
import xml.etree.ElementTree as ET


from models import InvCard, FixLog, InvLog
from search_card import SearchCard, Query
from elixir import session, setup_all, metadata
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func

setup_all()
app = Flask(__name__)

BASIC_LANDS = ["Plains", "Island", "Swamp", "Mountain", "Forest"]

#on application startup, load card descriptions
tree = ET.parse("/home/talin/Cockatrice/cards/cards.xml")
root = tree.getroot()
all_cards = filter(None,
		(SearchCard.from_xml_node(n)
		for n in root.findall("./cards/card")))

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/db_image/<int:img_id>')
def db_image(img_id):
	try:
		card = InvCard.query.filter_by(rowid=img_id).one()
		return send_file(StringIO(card.scan_png), 'image/png')
	except NoResultFound:
		return ("img not found", 404)

@app.route('/known_image/<set_abbrev>/<name>')
def known_image(set_abbrev,name):
	base_dir = '/home/talin/Cockatrice/cards/downloadedPics' #'' #YOUR BASE_DIR HERE
	sub_path = os.path.join(set_abbrev,name+'.full.jpg')
	path = safe_join(base_dir, sub_path)
	if os.path.exists(path):
		img = cv.LoadImage(path.encode('utf-8'), 0)
		return send_file(StringIO(cv.EncodeImage('.PNG',img).tostring()), 'image/png')
	else:
		return ("img not found", 404)


@app.route('/search')
def search():
	global all_cards

	query_text = request.args.get("q")
	if query_text is not None:
		query = Query.parse(query_text)
		cards = filter(query.matches_card, all_cards)
		cards = sorted(cards, key=lambda c: c.name)
	else:
		cards = []

	return render_template('search.html', cards=cards, query_text=query_text)

@app.route('/verify_scans', methods=['POST', 'GET'])
def verify_scans():
	if request.method == 'POST':
		#split_names = [name.split('_',1) + [val] for name,val in request.form]
		split_names = [name.split('_',1) + [val] for name,val in request.form.items()]
		by_rid = lambda (rid,x,y): rid
		d = {}
		for rid, args in  groupby(sorted(split_names, key=by_rid), by_rid):
			d[rid] = dict([a[1:] for a in list(args)])

		for rid, attribs in d.items():
			card = InvCard.query.filter_by(rowid=rid).one()
			if card.name != attribs['name'] or card.set_name != attribs['set_name']:
				FixLog(
						card = card,
						orig_set = card.set_name,
						orig_name = card.name,
						new_set = attribs['set_name'],
						new_name = attribs['name'],
						scan_png = card.scan_png
				)
				card.name = attribs['name']
				card.set_name = attribs['set_name']

			card.recognition_status = 'verified'
			session.commit()

	results = InvCard.query.filter_by(recognition_status='candidate_match').order_by('name').limit(50).all()
	return render_template('verify.html', cards=results)

#now the fun bit, where we pick boxes to reinsert into.
#the goal is to reuse existing boxes, and minimize the number of box seeks a human has to do.
#it would also be nice to keep existing groups of cards together.

#actually, I'll do that later. for now, naiively fill up the empties boxes we know about.
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


@app.route("/reinsert_cards", methods=["POST","GET"])
def reinsert_cards():
	if request.method == 'POST':
		#post. reinsert the given rowids
		now = datetime.now()
		reason = request.form["reason"]
		if not reason:
			raise Exception("reason required")

		#get the cards
		rids=[]
		for key, val in request.form.items():
			if key.startswith("reinsert_"):
				rids.append(int(key.split("_")[1]))
		cards = InvCard.query.filter(InvCard.rowid.in_(rids)).order_by('name').all()

		#make sure we can insert them
		if any(card.inventory_status != "temporarily_out" for card in cards):
			raise Exception("card is not temporarily out")

		box_capacity = list(metadata.bind.execute("select box,60 - count(*) as c from inv_cards where box not null group by box having c>0 order by c desc;"))
		
		#fill in each box with count cards
		i=0
		fill_orders = fit_boxes(box_capacity, len(cards))
		fill_orders = sorted(fill_orders, key=lambda (box,count): int(box))

		for box, count in fill_orders:
			max_index = session.query(func.max(InvCard.box_index)).filter_by(box='1').one()[0]
			for card in cards[i:count]:
				max_index += 1
				card.box = box
				card.box_index = max_index
				card.inventory_status = 'present'
				InvLog(card=card,date=now,direction='added',reason=reason)
			i+=count

		session.commit()

		#we're done. render the list.
		return render_template("results.html", cards=cards)

	else:
		#get the temporary_out cards to reinsert
		#it will be a list of ((date, reason), (cardlist)) tuples
		cards = InvCard.query.filter_by(inventory_status = "temporarily_out")
		the_key = lambda c: (c.most_recent_log().date, c.most_recent_log().reason)
		outstanding_cards = groupby(sorted(cards,the_key),the_key)
		outstanding_cards = [(key, sorted(val, key=attrgetter('name'))) for key, val in outstanding_cards]
		return render_template("outstanding_cards.html",outstanding_cards=outstanding_cards)
		



@app.route("/remove_cards", methods=["POST"])
def remove_cards():
	if request.method == 'POST':
		results = []

		now = datetime.now()
		reason = request.form['reason']
		if not reason:
			raise Exception("reason required")
		
		if not request.form['is_permanent']:
			raise Exception("is_permanent required")
		if request.form['is_permanent'] == 'yes':
			new_status = 'permanently_gone'
		else:
			new_status = 'temporarily_out'

		try:

			for key, val in request.form.items():
				match = re.match('remove_(?P<num>\d+)', key)
				if not match: #if this isn't remove_id
					continue
				if not val: #if the browser passed us an unchecked checkbox
					continue

				rid = int(match.group('num'))

				card = InvCard.query.filter_by(rowid=rid).one()
				if card.inventory_status != "present":
					raise Exception("can't remove non-present card")

				results.append({
					'rowid': card.rowid,
					'set_name': card.set_name,
					'name': card.name,
					'box': card.box,
					'box_index': card.box_index})

				card.box = None
				card.box_index = None
				card.inventory_status = new_status
				InvLog(card=card, direction='removed', reason=reason,date=now)
			session.commit()

			results = sorted(results, key = lambda r: (r['box'],r['box_index']))
			return render_template("results.html", cards=results)
		except Exception as e:
			session.rollback()
			raise e
			#todo. error page.


@app.route("/fetch_decklist")
def fetch_decklist():
	if request.args.get("url"):
		decklist = urllib2.urlopen(request.args.get("url")).read()
	else:
		decklist = request.args.get("decklist")
	
	results = {}
	sum_all = 0
	sum_have = 0

	if decklist:

		for line in decklist.splitlines():
			#get number and name of this card
			match = re.match('(?P<num>\d+) (?P<name>.*)',line)
			if match:
				num = int(match.group('num'))
				name = match.group('name')
			else:
				if line:
					num = 1
					name = line
				else:
					continue
			
			#skip basic lands
			if name in BASIC_LANDS:
				continue

			cards = InvCard.query.filter_by(name=name).filter(InvCard.inventory_status != "permanently_gone").all()
			results[name] = (cards, num)
			sum_all += num
			sum_have += min(num, len(cards))
	
	return render_template("fetch_decklist.html",decklist=decklist,results=results, total=(sum_have, sum_all))


if __name__ == '__main__':
	app.run(debug=True)
