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

import match_card
import cv
from models import InvCard
from elixir import setup_all, session
from sqlalchemy import distinct
import config

import os

if __name__ == '__main__':
	setup_all(True)

	sets = os.listdir(config.base_magic_set_dir)
	base_dir = config.base_magic_set_dir
	known = match_card.load_sets(base_dir, sets)
	cache = match_card.GradientCache(base_dir)
	print "all sets loaded!"

	cv.NamedWindow('debug')
	cv.StartWindowThread()
	match_card.match_db_cards(known, cache)
