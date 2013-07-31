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

from openexp.canvas import canvas
from openexp.keyboard import keyboard
from libopensesame import item, exceptions
from libqtopensesame import qtplugin

import math

def car2pol(x,y):
	
	"""Converts a Cartesian coordinate to a polar coordinate

	arguments
	x		--	x coordinate
	y		--	y coordinate
	
	returns
	r, phi	--	Polar (radial,angular) coordinates
	"""
	
	r = (x**2+y**2)**0.5
	phi = math.atan2(y,x)
	
	return r, phi

def pol2car(r, phi):
	
	"""Converts a polar coordinate to a Cartesian coordinate
	
	arguments
	r		--	radial coordinate
	phi		--	angular coordinate
	
	returns
	x, y		--	Cartesian (x,y) coordinates
	"""
	
	phi = math.radians(phi)
	
	x = r * math.cos(phi)
	y = r * math.sin(phi)
	
	return x, y


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


class frl(item.item):
	
	"""A plug-in to limit stimulus visibility using a forced retinal location"""
	
	def __init__(self, name, experiment, string=None):

		"""
		Constructor

		Arguments:
		name		--	item name
		experiment	--	an experiment object

		Keyword arguments:
		string		--	a definitional string (default=None)
		"""
		
		self.item_type = u"frl"
		self.sketchpad = u""
		self.timeout = 50000
		self.size = 150
		self.dist = 100
		self.angle = 45
		self.frltype = u'circle' # possibly add Gauss and raised cosine in future
		self.description = \
			u"Limits canvas visibility using a forced retinal location, until a key is pressed, or a timeout is reached"
		item.item.__init__(self, name, experiment, string)
	
	def prepare(self):

		"""
		Prepare the plug-in

		Returns:
		True
		"""

		item.item.prepare(self)
		
		# check for eyetracker
		if not hasattr(self.experiment, "eyetracker"):
			raise exceptions.runtime_error( \
				u"Please connect to the eyetracker using the the eyetracker_calibrate plugin before using the FRL plugin")
		
		# canvas
		self.cv = canvas(self.experiment)
		self.cv.copy(self.experiment.items[self.get(u'sketchpad')].canvas)
		self.drawcv = canvas(self.experiment)
		
		# keyboard
		self.kb = keyboard(self.experiment, keylist=None, timeout=1)
		
		# timeout
		self.notimeout = False
		if type(self.timeout) in [int, tuple]:
			if self.timeout <= 0:
				self.notimeout = True
		elif type(self.timeout) in [None, u'None']:
			self.notimeout = True
		else:
			raise exceptions.runtime_error( \
				u"FRL timeout should be an integer value (use None or 0 milliseconds for no timeout)")
		
		# FRL properties
		self.frlcor = pol2car(self.get(u'dist'), self.get(u'angle'))
		
		# psycho
		if self.get("canvas_backend") == u'psycho':
			# create Aperture
			from psychopy.visual import Aperture
			self.frl = Aperture(self.experiment.window, self.get(u'size'), pos=pos2psychopos(self.frlcor,self.experiment.resolution()), shape='circle', units='pix')
			# update function
			self.updatefunc = self.psychoupdate
			
		# legacy and xpyriment
		elif self.get("canvas_backend") in [u'legacy',u'xpyriment']:
			# PyGame specific properties
			self.r = self.get(u'size')/2
			self.h = 1 # updaterect height; increase to lower FRL resolution (which increases processing speed)
			# update function
			self.updatefunc = self.pygameupdate
			pass
		
		# any other backend produces an error
		else:
			raise exceptions.runtime_error( \
				u"Unsupported canvas backend: FRL plugin only supports legacy, psycho, and xpyriment backends")
		
		return True
	
	def pygameupdate(self, gazepos):
		
		"""update frl using PyGame; for internal use"""
		
		# frl position
		frlpos = (gazepos[0]-self.frlcor[0], gazepos[1]-self.frlcor[1])
		
		# clear canvas
		self.drawcv.clear()
				
		# top half
		for y in range(0,int(self.r/self.h)):
			y = self.r - y
			x = (self.r**2-y**2)**0.5
			updaterect = [frlpos[0]-x,frlpos[1]-self.h*y,2*x,self.h]
			self.drawcv.surface.set_clip(updaterect)
			self.drawcv.surface.blit(self.cv.surface,(0,0))
		# bottom half
		for y in range(0,int((self.r+1)/self.h)):
			x = (self.r**2-y**2)**0.5
			updaterect = [frlpos[0]-x,frlpos[1]+self.h*y,2*x,self.h]
			self.drawcv.surface.set_clip(updaterect)
			self.drawcv.surface.blit(self.cv.surface,(0,0))
		
		# unset clip and show canvas
		self.drawcv.surface.set_clip(None)
		self.drawcv.show()
		
	
	def psychoupdate(self, gazepos):
		
		"""update frl using PsychoPy; for internal use"""
		
		# frl position in PsychoPy coordinates
		gazepos = pos2psychopos(gazepos, self.experiment.resolution())
		frlpos = (gazepos[0]-self.frlcor[0], gazepos[1]+self.frlcor[1])
		# apply frl
		self.frl.setPos(frlpos)
		self.frl.enable()
		self.cv.show()
		self.frl.disable()
		
	
	def run(self):

		"""
		Run the plug-in

		Returns:
		True
		"""

		self.set_item_onset()
		
		stop = False
		t0 = self.time()
		
		while not stop:
			# get gaze position
			gazepos = self.experiment.eyetracker.sample()
			
			# update frl accordingly
			self.updatefunc(gazepos)
			
			# response
			response, t1 = self.kb.get_key()

			# timeout
			if (self.time() - t0 > self.timeout and not self.notimeout) or (response != None):
				stop = True
		
		self.experiment.set(u'response', response)
		self.experiment.set(u'response_time', t1-t0)
		
		return True
		

class qtfrl(frl, qtplugin.qtplugin):

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
		
		frl.__init__(self, name, experiment, string)
		qtplugin.qtplugin.__init__(self, __file__)

	def init_edit_widget(self):

		"""Initialize the controls"""

		self.lock = True
		qtplugin.qtplugin.init_edit_widget(self, False)
		self.add_line_edit_control("sketchpad", "Sketchpad", tooltip= \
			"The name of the sketchpad to present through the FRL")
		self.add_line_edit_control("timeout", "Timeout", tooltip= \
			"Amount of time after which the FRL display quits; set to 0 for no timeout")
		self.add_spinbox_control('size', \
			'FRL diameter', 0, 2000, suffix=' px', tooltip= \
			'The diameter of the forced retinal location cutout in pixels')
		self.add_spinbox_control('dist', \
			'FRL distance', 0, 2000, suffix=' px', tooltip= \
			'The distance between gaze position and FRL center in pixels')
		self.add_spinbox_control('angle', \
			'FRL angle', 0, 360, suffix=' degrees', tooltip= \
			'The deviation from a horizontal line (0 is a position to the left of the gaze position; 90 to the top; 180 to the right)')
		self.add_combobox_control("frltype", "FRL type", \
			['circle'], \
			tooltip = "Indicates the FRL type")
		
		# credits
		self.add_text("<br><br><small><b>Copyrights Edwin S. Dalmaijer, 2013. Based on PyGaze toolbox: http://www.fss.uu.nl/psn/pygaze/</b></small>")

		# pad empty space below controls
		self.add_stretch()
		
		self.lock = False

	def apply_edit_changes(self):

		"""Apply the controls"""

		if not qtplugin.qtplugin.apply_edit_changes(self, False) or self.lock:
			return
		self.experiment.main_window.refresh(self.name)

	def edit_widget(self):

		"""Update the controls"""

		self.lock = True
		qtplugin.qtplugin.edit_widget(self)
		self.lock = False
		return self._edit_widget