#!/usr/bin/python -tt
from elementtree import ElementTree
from subprocess import Popen, PIPE
from urllib2 import urlopen, URLError, HTTPError
from socket import gethostname
import yaml
import re

class Omreport:
	"""
	Use omreport to determine if system firmware is up-to-date

	"""

	def __init__(self):
		"""
		Grab XML output from omreport and store it

		"""

		self.storage_tree = self._system_xml('storage controller')
		self.system_tree = self._system_xml('system summary')
		self.model = self._system_model()
		self.hostname = gethostname()
		
	def _system_xml(self, report):
		"""
		Call omreport and storage output as an element tree
		@param: Report is a string, command line options for omreport

		"""

		try:
			output = Popen('omreport %s -fmt xml' % (report), stdout=PIPE, shell=True).communicate()[0]
		except OSError, e:
			print "Execution failure: %s" % (e)
			return
		try:
			root = ElementTree.fromstring(output)
			tree = ElementTree.ElementTree(root)
		except ExpatError, e:
			print "ExpatError: %s" % (e)
			return
		return tree
	
	def _system_model(self):
		"""
		Use facter to determine productname, i.e., r710, 2950 ,etc

		"""

		try:
			output = Popen("facter | awk '/productname/ {print $NF}'", stdout=PIPE, shell=True).communicate()[0]
		except OSError, e:
			print "Execution failure: %s" % (e)
			return
		return output.strip()

##########

def notify(om, yaml_data, mail_config):

	msg = "%s: \n" % (om.hostname)
	for error in om.errors:
		if 'bios' in error:
			msg += '	%s out of date, system version: %s -- current version: %s\n' \
			% ('BIOS', om.bios_ver, yaml_data['bios']) 	
		if 'perc' in error:
			msg += '	%s out of date, system version: %s -- current version: %s\n' \
			% (om.perc_name, om.perc_ver, yaml_data['percs'][om.perc_name])	
	
	mail = Popen('mail -s %s %s' % (mail_config['subject'], mail_config['to']), stdin=PIPE, shell=True)
	mail.communicate(msg)[0]

def main(types, mail_config):
	"""
	@param: dict that contains the name of controller type	
	Gather omreport data and compare to yaml data corresponding to this machines model

	"""

	om = Omreport()
	#om.model = '2950'
	om.errors = []
	pattern = re.compile(r'%s' % (types['controller']), re.I)
	url = "http://rhn.missouri.edu/pub/dell-yaml/%s.yaml" % (om.model)

	try:
		req = urlopen(url)
	except URLError, e:
		print ("URLError: %s") % (e)
	except HTTPError, e:
		print ("HTTPError: %s") % (e)

	yaml_data = yaml.load(req)

	# Gather PERC name and firmware version
	for node in om.storage_tree.findall('//Name'):
		if pattern.search(node.text):
			om.perc_name = node.text
			om.perc_ver = om.storage_tree.find('//FirmwareVer').text
	
	# BIOS version is easy
	om.bios_ver = om.system_tree.find('//SystemBIOS/Version').text
	
	# Compare with yaml_data
	if om.perc_name in yaml_data['percs']:
		if om.perc_ver < yaml_data['percs'][om.perc_name]:
			om.errors.append('perc')

	if om.bios_ver < yaml_data['bios']:
		om.errors.append('bios')
	
	if om.errors:
		notify(om, yaml_data, mail_config)

if __name__ == "__main__":
	types = {'controller': 'perc'}
	mail_config = {
		'subject': 'Firmware_report',
		'to': 'bakerlu@missouri.edu'
	}
	main(types, mail_config)
