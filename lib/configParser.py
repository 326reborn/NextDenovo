"""Configuration file parser."""
import re, os, sys
from kit import *

__all__ = ["ConfigParser"]

log = plog()

class ConfigParser:
	def __init__(self, cfgfile):
		self.cfg = self._defaultcfg()
		self.cfgdir = os.path.dirname(os.path.abspath(cfgfile))
		self.read(cfgfile)
		self._check()

	def _defaultcfg(cfg):
		cfg = {}
		cfg['job_type'] = 'sge'
		cfg['job_prefix'] = 'nextDenovo'
		cfg['task'] = 'all'
		cfg['rewrite'] = 1
		cfg['rerun'] = 3
		cfg['workdir'] = os.getcwd()
		cfg['read_cuoff'] = '1k'
		cfg['blocksize'] = '10g'
		cfg['pa_raw_align'] = '10'
		cfg['pa_correction'] = '3'
		cfg['nodelist'] = ''
		cfg['cluster_options'] = ''
		cfg['seed_cutfiles'] = cfg['pa_correction']
		cfg['correction_options'] = '-p 10'
		cfg['sort_options'] = '-m 40g -t 8 -k 40'
		return cfg

	def read(self, cfgfile):
		with open(cfgfile) as IN:
			for line in IN:
				line = line.strip()
				if not line or line[0].startswith('#'):
					continue
				group = re.search(r'([^;\s]+)\s*[=:]\s*([^;#\n]+)(\s*|#.*)$', line) # a option = value1 value2 # annotation
				if group:
					self.cfg[group.groups()[0]] = group.groups()[1].strip()

	def _check(self):
		if self.cfg['job_type'].lower() != 'local' and not self.cfg['cluster_options']:
			log.error('Error, failed find option: cluster_options')
			sys.exit(1)
		if 'sge_queue' not in self.cfg and '-q' in self.cfg['cluster_options']:
			self.cfg['sge_queue'] = parse_options_value(self.cfg['cluster_options'], '-q').split(',')

		self.cfg['seed_cutfiles'] = str(max(int(self.cfg['pa_correction']), int(self.cfg['seed_cutfiles'])))
		self.cfg['input_fofn'] = self.cfg['input_fofn'] if self.cfg['input_fofn'].startswith('/') else self.cfgdir + '/' + self.cfg['input_fofn']
		self.cfg['workdir'] = self.cfg['workdir'] if self.cfg['workdir'].startswith('/') else self.cfgdir + '/' + self.cfg['workdir']
		self.cfg['raw_aligndir'] = self.cfg['workdir'] + '/01.raw_align'
		self.cfg['cns_aligndir'] = self.cfg['workdir'] + '/02.cns_align'
		self.cfg['ctg_graphdir'] = self.cfg['workdir'] + '/03.ctg_graph'

		if 'usetempdir' in self.cfg:
			if str(self.cfg['usetempdir']).lower() in ['no', '0', 'false']:
				del self.cfg['usetempdir']
			elif self.cfg['job_type'].lower() == 'local':
				log.error('Error, usetempdir cannot be used with local.')
				sys.exit(1)
			else:
				if not self.cfg['usetempdir'].startswith('/'):
					log.error('Error, usetempdir must be absolute path')
					sys.exit(1)
				if self.cfg['job_type'] != 'sge' and not os.path.exists(self.cfg['nodelist']):
					log.error('Error, usetempdir must be used with nodelist for non-sge job_type.')
					sys.exit(1)

		if 'input_fofn' not in self.cfg or not os.path.exists(self.cfg['input_fofn']):
			log.error('Error, can not find input_fofn')
			sys.exit(1)

		if 'seed_cutoff' not in self.cfg:
			log.error('Error, failed find option: seed_cutoff')
			sys.exit(1)
		else:
			self.cfg['seed_cutoff'] = str(parse_num_unit(self.cfg['seed_cutoff']))

		if '-t' not in self.cfg['sort_options']:
			self.cfg['sort_options'] += ' -t 8'
		if '-m' not in self.cfg['sort_options']:
			self.cfg['sort_options'] += ' -m 40g'
		self.cfg['sort_threads'] = int(parse_options_value(self.cfg['sort_options'], '-t'))
		self.cfg['sort_mem'] = parse_options_value(self.cfg['sort_options'], '-m')

		if 'minimap2_options' not in self.cfg:
			log.error('Error, failed find option: minimap2_options')
			sys.exit(1)
		else:
			self.cfg['minimap2_threads'] = 3
			if '-t' in self.cfg['minimap2_options']:
				self.cfg['minimap2_threads'] = int(parse_options_value(self.cfg['minimap2_options'], '-t'))
			
			if '-x' not in self.cfg['minimap2_options']:
				log.error('Error, failed find \'-x\' option: minimap2_options')
				sys.exit(1)
			elif '-max_lq_length' not in self.cfg['correction_options']:
				if 'pb' in parse_options_value(self.cfg['minimap2_options'], '-x'):
					self.cfg['correction_options'] += ' -max_lq_length 1000'
				else:
					self.cfg['correction_options'] += ' -max_lq_length 10000'

		self.cfg['cns_threads'] = int(parse_options_value(self.cfg['correction_options'], '-p'))
		# if '-min_len_seed' not in self.cfg['correction_options']:
		# 	self.cfg['correction_options'] += ' -min_len_seed ' + self.cfg['seed_cutoff']

		if str(self.cfg['rewrite']).lower() in ['no', '0', 'false']:
			self.cfg['rewrite'] = 0
		else:
			self.cfg['rewrite'] = 1
			log.warning('Re-write workdir')
		
		if str(self.cfg['rerun']).lower() in ['no', '0', 'false']:
			self.cfg['rerun'] = 0
		else:
			self.cfg['rerun'] = min(int(self.cfg['rerun']), 10)

		if self.cfg['task'] not in ['all', 'correct', 'graph']:
			log.error('Error, task only accept: all|cns|graph')
			sys.exit(1)

		if self.cfg['input_type'] not in ['raw', 'corrected']:
			log.error('Error, input_type only accept: raw|corrected')
			sys.exit(1)
