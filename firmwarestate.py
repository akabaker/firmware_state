#!/usr/bin/python -tt
from elementtree import ElementTree
from subprocess import Popen, PIPE
from urllib2 import urlopen, URLError, HTTPError
from socket import gethostname
from email import MIMEMultipart, MIMEText
import smtplib
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
			output = Popen('/opt/dell/srvadmin/bin/omreport %s -fmt xml' % (report), stdout=PIPE, shell=True).communicate()[0]
		except OSError, e:
			print "Execution failure: %s" % (e)
			return
		try:
			root = ElementTree.fromstring(output)
			tree = ElementTree.ElementTree(root)
		except Exception, e:
			print "Exception: %s" % (e)
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

def notify(om, yaml_data, mail_config):

	tmpl = '-%s out of date, system version: %s -- latest version: %s <br>'
	msg = "<strong>%s</strong>: <br>" % (om.hostname)

	if 'bios' in om.errors:
		msg += (tmpl) % ('BIOS', om.bios_ver, yaml_data['bios'])

	if 'perc' in om.errors:
		for (key, val) in om.outofdate.items():
			msg += (tmpl) % (key, val, yaml_data['percs'][key])

	message = MIMEMultipart.MIMEMultipart('alternative')
	message['from'] = mail_config['from']
	message['to'] =  mail_config['to']
	message['subject'] = mail_config['subject']
	body = MIMEText.MIMEText(msg, 'html')
	message.attach(body)
	s = smtplib.SMTP('localhost')
	s.sendmail(message['from'], message['to'], message.as_string())
	s.quit()

def main(types, mail_config):
	"""

	Params: dict that contains the name of controller type, dict containing mail configuration
	Gather omreport data and compare to yaml data corresponding to this machines model

	"""

	om = Omreport()
	om.errors = []
	om.percs = {}
	om.outofdate = {}
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
	for node in om.storage_tree.findall('//DCStorageObject'):
		perc_name = node.find('Name').text
		perc_ver = node.find('FirmwareVer').text
		om.percs[perc_name] = perc_ver

	# BIOS version is easy
	om.bios_ver = om.system_tree.find('//SystemBIOS/Version').text
	
	# Compare with yaml_data
	for perc_name, version in om.percs.items():
		if version < yaml_data['percs'][perc_name]:
			om.errors.append('perc')
			om.outofdate[perc_name] = version

	if om.bios_ver < yaml_data['bios']:
		om.errors.append('bios')
	
	if om.errors:
		notify(om, yaml_data, mail_config)

if __name__ == "__main__":
	types = {'controller': 'perc'}
	mail_config = {
		'subject': 'Firmware_report',
		'to': 'bakerlu@missouri.edu',
		'from': 'root@%s' % (gethostname()),
	}
	main(types, mail_config)
