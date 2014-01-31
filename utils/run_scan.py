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

import cv
import scan_card

from elixir import session, setup_all
import sqlalchemy
from sqlalchemy import func
from models import *
import re

def captures_to_db(captures, box_name):
	#given an iterable of captures and a box name,
	#save all the captured images to the database
	starting_index = session.query(func.max(InvCard.box_index))\
			.filter(InvCard.box==box_name).first()[0]
	if starting_index is None:
		starting_index = 0

	for i, img in enumerate(captures):
		as_png = cv.EncodeImage(".png", img).tostring()

		InvCard(
				box = box_name,
				box_index = starting_index + i,
				scan_png = as_png,
				recognition_status = "scanned",
				inventory_status = "present")

	session.commit()

def capture_box(cam, boxnum):

	print "scanning %s" % boxnum
	while True: #retry loop
		retry = False
		captures = scan_card.watch_for_card(cam)
		print "captured %d cards. is this correct?" % len(captures)
		answer = raw_input()
		print "got answer: ", answer
		if re.search('[yc]',answer):
			break #finish the function
		else:
			while not re.match('[ra]', answer):
				print "(r)etry scan? or (a)bort?"
				answer = raw_input()
			if re.search('r',answer):
				continue
			elif re.search('a',answer):
				return #abort the scan
			#default will retry

	captures_to_db(captures, boxnum)



if __name__ == '__main__':
	setup_all(True)

	cam = cv.CreateCameraCapture(0)
	scan_card.setup_windows()

	#main loop
	while True:
		#for now, name the next box as the largest integer box name, +1
		current_max_box = session.query(func.max(sqlalchemy.cast(InvCard.box, sqlalchemy.Integer))).first()[0]
		if current_max_box is None:
			#if there is no current box, just start at 1
			next_box = 1
		else:
			next_box = current_max_box + 1

		print "box to scan[%02d]: " % next_box,
		answer = raw_input().rstrip()
		if answer != "":
			next_box = answer
		capture_box(cam, next_box)
