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

setup_all(True)

cam = cv.CreateCameraCapture(0)
scan_card.setup_windows()

def capture_box(cam, boxnum):
	while True: #retry loop
		retry = False
		captures = scan_card.watch_for_card(cam)
		scan_card.save_captures(boxnum, captures)
		print "captured %d cards. is this correct?" % len(captures)
		answer = raw_input()
		print "got answer: ", answer
		if re.search('[yc]',answer):
			break #finish the function
		else:
			print "try editing captures_%02d to match" % boxnum
			answer = ""
			while not re.match('[cra]', answer):
				print "when done - (c)orrected? (r)etry scan? or (a)bort?"
				answer = raw_input()
			if re.search('c',answer):
				break
			elif re.search('r',answer):
				continue
			elif re.search('a',answer):
				return #abort the scan
			#default will retry

	scan_card.folder_to_db(boxnum)


if __name__ == '__main__':
	#main loop
	while True:
		#for now, name the next box as the largest integer box name, +1
		current_max_box = session.query(func.max(sqlalchemy.cast(InvCard.box, sqlalchemy.Integer))).first()[0]
		if current_max_box is None:
			#if there is no current box, just start at 1
			next_box = 1
		else:
			next_box = current_max_box + 1
		print "scanning %02d" % next_box
		capture_box(cam, next_box)
