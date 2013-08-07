"""
This file is part of OpenSesame.

OpenSesame is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenSesame is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with OpenSesame.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy
from PyQt4 import QtCore, QtGui

from openexp.keyboard import keyboard
from libopensesame import item, exceptions
from libqtopensesame import qtplugin

def pos2psychopos(pos, dispsize):

	"""Returns a converted position tuple (x,y) (internal use)
	arguments
	pos		--	a (x,y) position tuple, assuming (0,0) is top left
	dispsize	--	a (width, height) tuple for the display resolution
				
	returns
	pos		--	a (x,y) tuple that makes sense to PsychoPy (i.e. (0,0) is
				display center; bottom left is (-,-) and top right is
				(+,+))
	"""
	
	x = pos[0] - dispsize[0]/2
	y = (pos[1] - dispsize[1]/2) * -1
	
	return (x,y)


def psychopos2pos(pos, dispsize):

	"""Returns a converted position tuple (x,y) (internal use)
	arguments
	pos		--	a (x,y) tuple that makes sense to PsychoPy (i.e. (0,0) is
				display center; bottom left is (-,-) and top right is
				(+,+))
	dispsize	--	a (width, height) tuple for the display resolution

	returns
	pos		--	a (x,y) position tuple, assuming (0,0) is top left
	"""
	
	x = pos[0] + dispsize[0]/2
	y = (pos[1] * -1) + dispsize[1]/2
	
	return (x,y)


class aoi(item.item):
	
	"""A plug-in to apply areas of interest"""
	
	def __init__(self, name, experiment, string=None):

		"""
		Constructor

		Arguments:
		name		--	item name
		experiment	--	an experiment object

		Keyword arguments:
		string		--	a definitional string (default=None)
		"""
		
		self.item_type = u"aoi"
		self.aoiname = u"AOI_0"
		self.x = 0
		self.y = 0
		self.w = 200
		self.h = 100
		self.newaoi = []
		self.description = \
			u"Define areas of interest (AOIs) with a rectangle shape"
		item.item.__init__(self, name, experiment, string)
		
		if hasattr(self.experiment, "aoidict"):
			self.aoidict = self.experiment.aoidict
		else:
			self.aoidict = {}
		self.aoinr = len(self.aoidict)
	
	def prepare(self):

		"""
		Prepare the plug-in

		Returns:
		True
		"""
		
		# check for eyetracker
		if not hasattr(self.experiment, "eyetracker"):
			raise exceptions.runtime_error( \
				u"Please connect to the eyetracker using the the eyetracker_calibrate plugin before using the AOI plugin")
		
		# keyboard
		self.kb = keyboard(self.experiment, keylist=None, timeout=1)
		
		# string to dict
		exec("self.aoidict = %s" % self.get("aoidictstr"))
		
		# create numpy arrays (for faster processing)
		blnkarray = numpy.array(numpy.zeros(len(self.aoidict)),dtype=numpy.int)
		self._lx = numpy.array(blnkarray, copy=True) # left x border
		self._rx = numpy.array(blnkarray, copy=True) # right x border
		self._ty = numpy.array(blnkarray, copy=True) # top y border
		self._by = numpy.array(blnkarray, copy=True) # bottom y border
		self._namelist = numpy.array(self.aoidict.keys())
		self._aoicount = numpy.zeros(len(self._namelist))
		self._notaoicount = 0
		
		for aoinr in range(0,len(self._namelist)):
			x, y, w, h = self.aoidict[self._namelist[aoinr]]
			self._lx[aoinr] = x
			self._rx[aoinr] = x + w
			self._ty[aoinr] = y
			self._by[aoinr] = y + h
				
		return True
	
	def run(self):

		"""
		Run the plug-in

		Returns:
		True
		"""
		
		stop = False
		t0 = self.time()
		
		while not stop:
			
			# wait for fixation
			fx, fy = self.experiment.eyetracker.wait_for_fixation_start()
			
			# check if fixpos is in an AOI
			xina = (self._lx < fx) == (self._rx > fx) # fixation between x borders
			yina = (self._by < fy) == (self._ty > fy) # fixation between y borders
			self._aoicount[xina&yina] += 1 # add one to the count of every fixated AOI
			
			# if no AOI is hit
			if sum(xina&yina) == 0:
				self._notaoicount += 1
			
			# response
			response, t1 = self.kb.get_key()

			# timeout
			if (self.time() - t0 > self.timeout and not self.notimeout) or (response != None):
				stop = True
		
		self.experiment.set(u'response', response)
		self.experiment.set(u'response_time', t1-t0)
		
		return True
		

class qtaoi(aoi, qtplugin.qtplugin):

	"""GUI part of the plug-in"""

	def __init__(self, name, experiment, string=None):

		"""
		Constructor

		Arguments:
		name		--	item name
		experiment	--	an experiment object

		Keyword arguments:
		string		--	a definitional string (default=None)
		"""
		
		aoi.__init__(self, name, experiment, string)
		qtplugin.qtplugin.__init__(self, __file__)
		

	def init_edit_widget(self):

		"""Initialize the controls"""

		self.lock = True
		qtplugin.qtplugin.init_edit_widget(self, False)
		self.add_line_edit_control("aoiname", "AOI name", tooltip= \
			"The name of the new AOI", default="aoi_%d" % self.aoinr)
		self.add_spinbox_control("x", "X position", 0, 10000, suffix=' px', \
			tooltip= "The horizontal coordinate of the AOI")
		self.add_spinbox_control("y", "Y position", 0, 10000, suffix=' px', \
			tooltip= "The vertical coordinate of the AOI")
		self.add_spinbox_control('w', \
			'width', 0, 2000, suffix=' px', tooltip= \
			'The width of the AOI')
		self.add_spinbox_control('h', \
			'height', 0, 2000, suffix=' px', tooltip= \
			'The height of the AOI')
		
		# add button
		# PyQt4 stuff
		button = QtGui.QPushButton(self.experiment.icon(u'add'), u'Add AOI')
		button.setIconSize(QtCore.QSize(16, 16))
		button.clicked.connect(self.add_aoi)
		hbox = QtGui.QHBoxLayout()
		hbox.setMargin(0)
		hbox.addWidget(button)
		widget = QtGui.QWidget()
		widget.setLayout(hbox)
		# libqtopensesame.items.qtplugin.qtplugin
		self.add_control("", widget, "click button to add new AOI") # label, widget, tooltip: label is empty, since text is on button
		
		# inactive line edit, showing number of AOIs
		self.aoi_nr_display = self.add_line_edit_control("aoinr", "number of AOIs", \
			tooltip = "The number of AOIs that you have currently defined")
		self.aoi_nr_display.setDisabled(True)
		
		# reset button
		# PyQt4 stuff
		button = QtGui.QPushButton(self.experiment.icon(u'delete'), u'Reset')
		button.setIconSize(QtCore.QSize(16, 16))
		button.clicked.connect(self.clear_aois)
		hbox = QtGui.QHBoxLayout()
		hbox.setMargin(0)
		hbox.addWidget(button)
		widget = QtGui.QWidget()
		widget.setLayout(hbox)
		# libqtopensesame.items.qtplugin.qtplugin
		self.add_control("", widget, "click button to delete all AOI") # label, widget, tooltip: label is empty, since text is on button
		
		# credits
		self.add_text("<br><br><small><b>Copyrights Edwin S. Dalmaijer, 2013. Based on PyGaze toolbox: http://www.fss.uu.nl/psn/pygaze/</b></small>")

		# pad empty space below controls
		self.add_stretch()
		
#		# AOI list
#		self.add_text("<b>AOI list</b>")
#		for aoi in self._aoidict.keys():
#			x, y, w, h = self._aoidict[aoi]
#			self.add_text("%s: x=%d, y=%d, w=%d, h=%d" % (aoi, x, y, w, h))
		
		self.lock = False
		
	def add_aoi(self):

		# bookkeeping		
		self.aoidict[self.aoiname] = [self.x, self.y, self.w, self.h]
		self.set("aoinr", len(self.aoidict))
		self.set("aoidictstr", self.aoidict)
		#self.experiment.aoidict = self.aoidict
		
		# gui
#		self.add_text("%s: x=%d, y=%d, w=%d, h=%d" % (self.aoiname), self.x, self.y, self.w, self.h)
		self.edit_widget()
		self.apply_edit_changes()
	
	def clear_aois(self):
		
		# bookkeeping
		self.aoidict = {}
		self.set("aoinr", len(self.aoidict))
		self.set("aoidictstr", self.aoidict)

		# gui
		self.edit_widget()
		self.apply_edit_changes()

	def apply_edit_changes(self):

		"""Apply the controls"""

		if not qtplugin.qtplugin.apply_edit_changes(self, False) or self.lock:
			return
		
		self.experiment.main_window.refresh(self.name)

	def edit_widget(self):

		"""Update the controls"""

		# unlock
		self.lock = True
		# edit
		qtplugin.qtplugin.edit_widget(self)
		# lock
		self.lock = False
		return self._edit_widget