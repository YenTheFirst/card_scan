# -*- coding: utf-8 -*-
from flask import Flask, send_file, safe_join, render_template, request
import sqlite3
from StringIO import StringIO
import os
import cv
from itertools import groupby
import re
from datetime import datetime

from models import InvCard, FixLog, InvLog
from elixir import session, setup_all
from sqlalchemy.orm.exc import NoResultFound

setup_all()
app = Flask(__name__)

BASIC_LANDS = ["Plains", "Island", "Swamp", "Mountain", "Forest"]

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
	page_size = 10;
	connection = sqlite3.connect('inventory.sqlite3')
	cursor = connection.cursor()
	cols = ['rowid', 'name', 'set_name', 'box', 'box_index', 'recognition_status']
	where_clause = ""
	where_params = []
	for key in cols:
		val = request.args.get(key)
		if val is not None:
			if len(where_params) == 0:
				where_clause = " where "
			else:
				where_clause += " and "
			where_clause += (key + " = ?")
			where_params.append(val)
	query = "select %s from inv_cards" % ", ".join(cols)
	query += where_clause
	
	page_num = 0
	val = request.args.get("page")
	if val is not None: 
		page_num = int(val)-1
	query += " limit ? offset ?";

	print query
	print page_num * page_size
	cursor.execute(query, where_params+[page_size, page_num*page_size])
	results = [dict(zip(cols,r)) for r in cursor.fetchall()]
	return render_template('results.html', cards=results)

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

			return render_template("removed_cards.html", removed_list=results)
		except Exception as e:
			session.rollback()
			raise e
			#todo. error page.


@app.route("/fetch_decklist")
def fetch_decklist():
	decklist = request.args.get("decklist")
	results = {}

	if decklist:

		for line in decklist.splitlines():
			#get number and name of this card
			match = re.match('(?P<num>\d+) (?P<name>.*)',line)
			if match:
				num = int(match.group('num'))
				name = match.group('name')
			else:
				num = 1
				name = line
			
			#skip basic lands
			if name in BASIC_LANDS:
				continue

			results[name] = (InvCard.query.filter_by(name=name).all(), num)
	
	return render_template("fetch_decklist.html",decklist=decklist,results=results)


if __name__ == '__main__':
	app.run(debug=True)
