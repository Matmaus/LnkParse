#!/usr/bin/env python3
# 2016 - Silas Cutler (silas.cutler@blacklistthisdomain.com)

__description__ = 'Windows Shortcut file (LNK) parser'
__author__ = 'Silas Cutler'
__version__ = '0.2.1'

import sys
import json
import struct
import datetime
import argparse


class lnk_file(object):
	def __init__(self, fhandle=None, indata=None, debug=False):
		self.define_static()

		if fhandle:
			self.indata = fhandle.read()
		elif indata:
			self.indata = indata

		self.debug = debug
		self.lnk_header = {}

		self.linkFlag = {
			'HasTargetIDList': False,
			'HasLinkInfo': False,
			'HasName': False,
			'HasRelativePath': False,
			'HasWorkingDir': False,
			'HasArguments': False,
			'HasIconLocation': False,
			'IsUnicode': False,
			'ForceNoLinkInfo': False,
			'HasExpString': False,
			'RunInSeparateProcess': False,
			'Reserved0': False,
			'HasDarwinID': False,
			'RunAsUser': False,
			'HasExpIcon': False,
			'NoPidlAlias': False,
			'Reserved1': False,
			'RunWithShimLayer': False,
			'ForceNoLinkTrack': False,
			'EnableTargetMetadata': False,
			'DisableLinkPathTracking': False,
			'DisableKnownFolderTracking': False,
			'DisableKnownFolderAlias': False,
			'AllowLinkToLink': False,
			'UnaliasOnSave': False,
			'PreferEnvironmentPath': False,
			'KeepLocalIDListForUNCTarget': False,
		}
		self.fileFlag = {
			'FILE_ATTRIBUTE_READONLY': False,
			'FILE_ATTRIBUTE_HIDDEN': False,
			'FILE_ATTRIBUTE_SYSTEM': False,
			'Reserved, not used by the LNK format': False,
			'FILE_ATTRIBUTE_DIRECTORY': False,
			'FILE_ATTRIBUTE_ARCHIVE': False,
			'FILE_ATTRIBUTE_DEVICE': False,
			'FILE_ATTRIBUTE_NORMAL': False,
			'FILE_ATTRIBUTE_TEMPORARY': False,
			'FILE_ATTRIBUTE_SPARSE_FILE': False,
			'FILE_ATTRIBUTE_REPARSE_POINT': False,
			'FILE_ATTRIBUTE_COMPRESSED': False,
			'FILE_ATTRIBUTE_OFFLINE': False,
			'FILE_ATTRIBUTE_NOT_CONTENT_INDEXED': False,
			'FILE_ATTRIBUTE_ENCRYPTED': False,
			'Unknown (seen on Windows 95 FAT)': False,
			'FILE_ATTRIBUTE_VIRTUAL': False,
		}

		self.targets = {
			'size': 0,
			'items': [],
		}

		self.loc_information = {}
		self.data = {}
		self.extraBlocks = {}

		self.process()
		self.define_common()


	def define_common(self):
		try:
			out = ''
			if self.linkFlag['HasRelativePath']:
				out += self.data['relativePath']
			if self.linkFlag['HasArguments']:
				out += ' ' + self.data['commandLineArguments']

			self.lnk_command = out
		except Exception as e:
			if self.debug:
				print('Exception define_common: %s' % e)


	def get_command(self):
		try:
			out = ''
			if self.linkFlag['HasRelativePath']:
				out += self.data['relativePath']
			if self.linkFlag['HasArguments']:
				out += ' ' + self.data['commandLineArguments']

			return out
		except Exception as e:
			if self.debug:
				print('Exception get_command: %s' % (e))
			return ''


	def define_static(self):
		# Define static constents used within the LNK format

		# Each MAGIC string refernces a function for processing
		self.EXTRA_SIGS = {
			'a0000001': self.parse_environment_block,
			'a0000002': self.parse_console_block,
			'a0000003': self.parse_distributedTracker_block,
			'a0000004': self.parse_codepage_block,
			'a0000005': self.parse_specialFolder_block,
			'a0000006': self.parse_darwin_block,
			'a0000007': self.parse_icon_block,
			'a0000008': self.parse_shimLayer_block,
			'a0000009': self.parse_metadata_block,
			'a000000b': self.parse_knownFolder_block,
			'a000000c': self.parse_shellItem_block,
		}

		self.DRIVE_TYPES = [
			'DRIVE_UNKNOWN',
			'DRIVE_NO_ROOT_DIR',
			'DRIVE_REMOVABLE',
			'DRIVE_FIXED',
			'DRIVE_REMOTE',
			'DRIVE_CDROM',
			'DRIVE_RAMDISK',
		]
		self.HOTKEY_VALUES = {
			'\x00': 'UNSET',
			'\x01': 'HOTKEYF_SHIFT',
			'\x02': 'HOTKEYF_CONTROL',
			'\x03': 'HOTKEYF_ALT',
		}
		self.WINDOWSTYLES = [
			'SW_HIDE',
			'SW_NORMAL',
			'SW_SHOWMINIMIZED',
			'SW_MAXIMIZE ',
			'SW_SHOWNOACTIVATE',
			'SW_SHOW',
			'SW_MINIMIZE',
			'SW_SHOWMINNOACTIVE',
			'SW_SHOWNA',
			'SW_RESTORE',
			'SW_SHOWDEFAULT',
		]


	@staticmethod
	def clean_line(rstring):
		return ''.join(chr(i) for i in rstring if 128 > i > 20)


	def parse_lnk_header(self):
		# Parse the LNK file header
		try:
			# Header always starts with { 4c 00 00 00 } and is the size of the header
			self.lnk_header['header_size'] = struct.unpack('<I', self.indata[:4])[0]

			lnk_header = self.indata[:self.lnk_header['header_size']]

			self.lnk_header['guid'] = lnk_header[4:20].hex()

			self.lnk_header['rlinkFlags'] = struct.unpack('<i', lnk_header[20:24])[0]
			self.lnk_header['rfileFlags'] = struct.unpack('<i', lnk_header[24:28])[0]

			self.lnk_header['creation_time'] = struct.unpack('<q', lnk_header[28:36])[0]
			self.lnk_header['accessed_time'] = struct.unpack('<q', lnk_header[36:44])[0]
			self.lnk_header['modified_time'] = struct.unpack('<q', lnk_header[44:52])[0]

			self.lnk_header['file_size'] = struct.unpack('<i', lnk_header[52:56])[0]
			self.lnk_header['rfile_size'] = lnk_header[52:56].hex()

			self.lnk_header['icon_index'] = struct.unpack('<I', lnk_header[56:60])[0]
			try:
				if struct.unpack('<i', lnk_header[60:64])[0] < len(self.WINDOWSTYLES):
					self.lnk_header['windowstyle'] = self.WINDOWSTYLES[
						struct.unpack('<i', lnk_header[60:64])[0]]
				else:
					self.lnk_header['windowstyle'] = struct.unpack('<i', lnk_header[60:64])[0]
			except Exception as e:
				if self.debug:
					print('Error Parsing WindowStyle in Header: %s' % e)
				self.lnk_header['windowstyle'] = struct.unpack('<i', lnk_header[60:64])[0]

			try:
				self.lnk_header['hotkey'] = '%s - %s {0x%s}' % (
					self.HOTKEY_VALUES[chr(struct.unpack('<B', lnk_header[65:66])[0])],
					self.clean_line(struct.unpack('<B', lnk_header[64:65])),
					lnk_header[64:66].hex()
				)

				self.lnk_header['rhotkey'] = struct.unpack('<H', lnk_header[64:66])[0]
			except Exception as e:
				if self.debug:
					print('Exception parsing HOTKEY part of header: %s' % e)
					print(lnk_header[65:66].hex())
				self.lnk_header['hotkey'] = hex(struct.unpack('<H', lnk_header[64:66])[0])
				self.lnk_header['rhotkey'] = struct.unpack('<H', lnk_header[64:66])[0]

			self.lnk_header['reserved0'] = struct.unpack('<H', lnk_header[66:68])[0]
			self.lnk_header['reserved1'] = struct.unpack('<i', lnk_header[68:72])[0]
			self.lnk_header['reserved2'] = struct.unpack('<i', lnk_header[72:76])[0]
		except Exception as e:
			if self.debug:
				print('Exception parsing LNK Header: %s' % e)
			return False

		if self.lnk_header['header_size'] == 76:
			return True


	def parse_link_flags(self):
		if self.lnk_header['rlinkFlags'] & 0x00000001:
			self.linkFlag['HasTargetIDList'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000002:
			self.linkFlag['HasLinkInfo'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000004:
			self.linkFlag['HasName'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000008:
			self.linkFlag['HasRelativePath'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000010:
			self.linkFlag['HasWorkingDir'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000020:
			self.linkFlag['HasArguments'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000040:
			self.linkFlag['HasIconLocation'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000080:
			self.linkFlag['IsUnicode'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000100:
			self.linkFlag['ForceNoLinkInfo'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000200:
			self.linkFlag['HasExpString'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000400:
			self.linkFlag['RunInSeparateProcess'] = True
		if self.lnk_header['rlinkFlags'] & 0x00000800:
			self.linkFlag['Reserved0'] = True
		if self.lnk_header['rlinkFlags'] & 0x00001000:
			self.linkFlag['HasDarwinID'] = True
		if self.lnk_header['rlinkFlags'] & 0x00002000:
			self.linkFlag['RunAsUser'] = True
		if self.lnk_header['rlinkFlags'] & 0x00004000:
			self.linkFlag['HasExpIcon'] = True
		if self.lnk_header['rlinkFlags'] & 0x00008000:
			self.linkFlag['NoPidlAlias'] = True
		if self.lnk_header['rlinkFlags'] & 0x000100000:
			self.linkFlag['Reserved1'] = True

		if self.lnk_header['rlinkFlags'] & 0x00020000:
			self.linkFlag['RunWithShimLayer'] = True
		if self.lnk_header['rlinkFlags'] & 0x00040000:
			self.linkFlag['ForceNoLinkTrack'] = True
		if self.lnk_header['rlinkFlags'] & 0x00080000:
			self.linkFlag['EnableTargetMetadata'] = True
		if self.lnk_header['rlinkFlags'] & 0x00100000:
			self.linkFlag['DisableLinkPathTracking'] = True
		if self.lnk_header['rlinkFlags'] & 0x00200000:
			self.linkFlag['DisableKnownFolderTracking'] = True
		if self.lnk_header['rlinkFlags'] & 0x00400000:
			self.linkFlag['DisableKnownFolderAlias'] = True
		if self.lnk_header['rlinkFlags'] & 0x00800000:
			self.linkFlag['AllowLinkToLink'] = True
		if self.lnk_header['rlinkFlags'] & 0x01000000:
			self.linkFlag['UnaliasOnSave'] = True
		if self.lnk_header['rlinkFlags'] & 0x02000000:
			self.linkFlag['PreferEnvironmentPath'] = True
		if self.lnk_header['rlinkFlags'] & 0x04000000:
			self.linkFlag['KeepLocalIDListForUNCTarget'] = True

		self.lnk_header['linkFlags'] = self.enabled_flags_to_list(self.linkFlag)


	def parse_file_flags(self):
		if self.lnk_header['rfileFlags'] & 0x00000001:
			self.fileFlag['FILE_ATTRIBUTE_READONLY'] = True
		if self.lnk_header['rfileFlags'] & 0x00000002:
			self.fileFlag['FILE_ATTRIBUTE_HIDDEN'] = True
		if self.lnk_header['rfileFlags'] & 0x00000004:
			self.fileFlag['FILE_ATTRIBUTE_SYSTEM'] = True
		if self.lnk_header['rfileFlags'] & 0x00000008:
			self.fileFlag['Reserved, not used by the LNK format'] = True
		if self.lnk_header['rfileFlags'] & 0x00000010:
			self.fileFlag['FILE_ATTRIBUTE_DIRECTORY'] = True
		if self.lnk_header['rfileFlags'] & 0x00000020:
			self.fileFlag['FILE_ATTRIBUTE_ARCHIVE'] = True
		if self.lnk_header['rfileFlags'] & 0x00000040:
			self.fileFlag['FILE_ATTRIBUTE_DEVICE'] = True
		if self.lnk_header['rfileFlags'] & 0x00000080:
			self.fileFlag['FILE_ATTRIBUTE_NORMAL'] = True
		if self.lnk_header['rfileFlags'] & 0x00000100:
			self.fileFlag['FILE_ATTRIBUTE_TEMPORARY'] = True
		if self.lnk_header['rfileFlags'] & 0x00000200:
			self.fileFlag['FILE_ATTRIBUTE_SPARSE_FILE'] = True
		if self.lnk_header['rfileFlags'] & 0x00000400:
			self.fileFlag['FILE_ATTRIBUTE_REPARSE_POINT'] = True
		if self.lnk_header['rfileFlags'] & 0x00000800:
			self.fileFlag['FILE_ATTRIBUTE_COMPRESSED'] = True
		if self.lnk_header['rfileFlags'] & 0x00001000:
			self.fileFlag['FILE_ATTRIBUTE_OFFLINE'] = True
		if self.lnk_header['rfileFlags'] & 0x00002000:
			self.fileFlag['FILE_ATTRIBUTE_NOT_CONTENT_INDEXED'] = True
		if self.lnk_header['rfileFlags'] & 0x00004000:
			self.fileFlag['FILE_ATTRIBUTE_ENCRYPTED'] = True
		if self.lnk_header['rfileFlags'] & 0x00008000:
			self.fileFlag['Unknown (seen on Windows 95 FAT)'] = True
		if self.lnk_header['rfileFlags'] & 0x00010000:
			self.fileFlag['FILE_ATTRIBUTE_VIRTUAL'] = True

		self.lnk_header['fileFlags'] = self.enabled_flags_to_list(self.fileFlag)


	def parse_link_information(self):
		index = 0
		while True:
			tmp_item = {}
			tmp_item['size'] = struct.unpack('<H', self.link_target_list[index: index + 2])[0]
			tmp_item['rsize'] = self.link_target_list[index: index + 2].hex()

			self.items.append(tmp_item)
			index += tmp_item['size']

			return ''


	# Still in development // repair
	def parse_targets(self, index):
		max_size = self.targets['size'] + index

		while ( index  < max_size ):
			ItemID = {
				"size": struct.unpack('<H', self.indata[index : index + 2])[0] ,
				"type": struct.unpack('<B', self.indata[index + 2 : index + 3])[0] ,
					}
			index += 3

#			self.targets['items'].append( self.indata[index: index + ItemID['size']].replace('\x00','') )
#			print "[%s] %s" % (ItemID['size'], hex(ItemID['type']) )#, self.indata[index: index + ItemID['size']].replace('\x00','') )
#			print self.indata[ index: index + ItemID['size'] ].encode('hex')[:50]
			index += ItemID['size']
#			print self.indata[index + 2: index + 2 + ItemID['size']].replace('\x00','')


	def process(self):
		index = 0
		if not self.parse_lnk_header():
			print('Failed Header Check')

		self.parse_link_flags()
		self.parse_file_flags()
		index += self.lnk_header['header_size']

		# Parse ID List
		if self.linkFlag['HasTargetIDList']:
			try:
				self.targets['size'] = struct.unpack('<H', self.indata[index: index + 2])[0]
				index += 2
				if self.debug:
					self.parse_targets(index)
				index += self.targets['size']
			except Exception as e:
				if self.debug:
					print('Exception parsing TargetIDList: %s' % e)
				return False

		if self.linkFlag['HasLinkInfo'] and self.linkFlag['ForceNoLinkInfo'] == False:
			try:
				self.loc_information = {
					'LinkInfoSize': struct.unpack('<i', self.indata[index: index + 4])[0],
					'LinkInfoHeaderSize': struct.unpack('<i', self.indata[index + 4: index + 8])[0],
					'LinkInfoFlags': struct.unpack('<i', self.indata[index + 8: index + 12])[0],
					'VolumeIDOffset': struct.unpack('<i', self.indata[index + 12: index + 16])[0],
					'LocalBasePathOffset': struct.unpack('<i', self.indata[index + 16: index + 20])[0],
					'CommonNetworkRelativeLinkOffset': struct.unpack('<i', self.indata[index + 20: index + 24])[0],
					'CommonPathSuffixOffset': struct.unpack('<i', self.indata[index + 24: index + 28])[0],
				}

				if self.loc_information['LinkInfoFlags'] & 0x0001:
					if self.loc_information['LinkInfoHeaderSize'] >= 36:
						self.loc_information['o_LocalBasePathOffsetUnicode'] = \
								struct.unpack('<i', self.indata[index + 28: index + 32])[0]
						local_index = index + self.loc_information['o_LocalBasePathOffsetUnicode']
						self.loc_information['o_LocalBasePathUnicode'] = \
								struct.unpack('<i', self.indata[local_index: local_index + 4])[0]
					else:
						local_index = index + self.loc_information['LocalBasePathOffset']
						self.loc_information['LocalBasePath'] = self.read_string(local_index)

					local_index = index + self.loc_information['VolumeIDOffset']
					self.loc_information['location'] = 'VolumeIDAndLocalBasePath'
					self.loc_information['location_info'] = {
						'VolumeIDSize':
							struct.unpack('<i', self.indata[local_index + 0: local_index + 4])[0],
						'rDriveType':
							struct.unpack('<i', self.indata[local_index + 4: local_index + 8])[0],
						'DriveSerialNumber': hex(
							struct.unpack('<i', self.indata[local_index + 8: local_index + 12])[0]),
						'VolumeLabelOffset':
							struct.unpack('<i', self.indata[local_index + 12: local_index + 16])[0],
					}

					if self.loc_information['location_info']['rDriveType'] < len(self.DRIVE_TYPES):
						self.loc_information['location_info']['DriveType'] = self.DRIVE_TYPES[self.loc_information['location_info']['rDriveType']]

					if self.loc_information['location_info']['VolumeLabelOffset'] != 20:
						length = self.loc_information['location_info']['VolumeIDSize'] - self.loc_information['location_info']['VolumeLabelOffset']
						local_index = index + self.loc_information['VolumeIDOffset'] + self.loc_information['location_info']['VolumeLabelOffset']
						self.loc_information['location_info']['VolumeLabel'] = self.clean_line(self.indata[local_index: local_index + length].replace(b'\x00', b''))
					else:
						self.loc_information['location_info']['o_VolumeLabelOffsetUnicode'] = struct.unpack('<i', self.indata[local_index + 16: local_index + 20])[0]
						local_index = index + self.loc_information['VolumeIDOffset'] + self.loc_information['location_info']['o_VolumeLabelOffsetUnicode']
						self.loc_information['location_info']['o_VolumeLabelUnicode'] = struct.unpack('<i', self.indata[local_index: local_index + 4])[0]

				elif self.loc_information['LinkInfoFlags'] & 0x0002:
					if self.loc_information['LinkInfoHeaderSize'] >= 36:
						self.loc_information['o_CommonPathSuffixOffsetUnicode'] = \
								struct.unpack('<i', self.indata[index + 28: index + 32])[0]
						local_index = index + self.loc_information['o_CommonPathSuffixOffsetUnicode']
						self.loc_information['o_CommonPathSuffixUnicode'] = struct.unpack('<i', self.indata[local_index: local_index + 4])[0]
					else:
						local_index = index + self.loc_information['CommonPathSuffixOffset']
						self.loc_information['CommonPathSuffix'] = \
								struct.unpack('<i', self.indata[local_index: local_index + 4])[0]

					local_index = index + self.loc_information['CommonNetworkRelativeLinkOffset']
					self.loc_information['location'] = 'CommonNetworkRelativeLinkAndPathSuffix'
					self.loc_information['location_info'] = {
						'CommonNetworkRelativeLinkSize':
							struct.unpack('<i', self.indata[local_index + 0: local_index + 4])[0],
						'CommonNetworkRelativeLinkFlags':
							struct.unpack('<i', self.indata[local_index + 4: local_index + 8])[0],
						'NetNameOffset':
							struct.unpack('<i', self.indata[local_index + 8: local_index + 12])[0],
						'DeviceNameOffset':
							struct.unpack('<i', self.indata[local_index + 12: local_index + 16])[0],
						'NetworkProviderType':
							struct.unpack('<i', self.indata[local_index + 16: local_index + 20])[0],
					}

					if self.loc_information['location_info']['o_NetNameOffset'] > 20:
						self.loc_information['location_info']['o_NetNameOffsetUnicode'] = \
						struct.unpack('<i', self.indata[local_index + 20: index + 24])[0]
						local_index = index + self.loc_information['location_info']['o_NetNameOffsetUnicode']
						self.loc_information['location_info']['o_NetNameOffsetUnicode'] = \
							struct.unpack('<i', self.indata[local_index: local_index + 4])[0]

						self.loc_information['location_info']['o_DeviceNameOffsetUnicode'] = \
						struct.unpack('<i', self.indata[local_index + 24: index + 28])[0]
						local_index = self.loc_information['location_info']['o_DeviceNameOffsetUnicode']
						self.loc_information['location_info']['o_DeviceNameOffsetUnicode'] = \
							struct.unpack('<i', self.indata[local_index: local_index + 4])[0]
					else:
						local_index = index + self.loc_information['location_info']['o_NetNameOffset']
						self.loc_information['location_info']['o_NetNameOffset'] = \
							struct.unpack('<i', self.indata[local_index: local_index + 4])[0]

						local_index = self.loc_information['location_info']['o_DeviceNameOffset']
						self.loc_information['location_info']['o_DeviceNameOffset'] = \
							struct.unpack('<i', self.indata[local_index: local_index + 4])[0]

				index += (self.loc_information['LinkInfoSize'])

			except Exception as e:
				if self.debug:
					print('Exception parsing Location information: %s' % e)
				return False

		try:
			u_mult = 1
			if self.linkFlag['IsUnicode']:
				u_mult = 2

			if self.linkFlag['HasName']:
				index, self.data['description'] = self.read_stringData(index, u_mult)

			if self.linkFlag['HasRelativePath']:
				index, self.data['relativePath'] = self.read_stringData(index, u_mult)

			if self.linkFlag['HasWorkingDir']:
				index, self.data['workingDirectory'] = self.read_stringData(index, u_mult)

			if self.linkFlag['HasArguments']:
				index, self.data['commandLineArguments'] = self.read_stringData(index, u_mult)

			if self.linkFlag['HasIconLocation']:
				index, self.data['iconLocation'] = self.read_stringData(index, u_mult)

		except Exception as e:
			if self.debug:
				print('Exception in parsing data: %s' % e)
			return False

		try:
			while index <= len(self.indata) - 10:
				try:
					size = struct.unpack('<I', self.indata[index: index + 4])[0]
					sig = str(hex(struct.unpack('<I', self.indata[index + 4: index + 8])[0]))[2:]
					self.EXTRA_SIGS[sig](index, size)

					index += (size)
				except Exception as e:
					if self.debug:
						print('Exception in EXTRABLOCK Parsing: %s ' % e)
					index = len(self.data)
					break
		except Exception as e:
			if self.debug:
				print('Exception in EXTRABLOCK: %s' % e)


	def parse_environment_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x00000314                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000001                              |
		--------------------------------------------------------------------------------------------------
		|                                      <str> TargetAnsi                                          |
		|                                           260 B                                                |
		--------------------------------------------------------------------------------------------------
		|                                <unicode_str> TargetUnicode                                     |
		|                                           520 B                                                |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['ENVIRONMENTAL_VARIABLES_LOCATION_BLOCK'] = {}
		self.extraBlocks['ENVIRONMENTAL_VARIABLES_LOCATION_BLOCK']['size'] = size
		self.extraBlocks['ENVIRONMENTAL_VARIABLES_LOCATION_BLOCK']['TargetAnsi'] = self.read_string(index + 8)
		self.extraBlocks['ENVIRONMENTAL_VARIABLES_LOCATION_BLOCK']['TargetUnicode'] = self.read_unicode_string(index + 268)


	def parse_console_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x000000CC                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000002                              |
		--------------------------------------------------------------------------------------------------
		|         <u_int16> FillAttributes             |        <u_int16> PopupFillAttributes            |
		--------------------------------------------------------------------------------------------------
		|         <int16> ScreenBufferSizeX            |             <int16> ScreenBufferSizeY           |
		|             <int16> WindowSizeX              |               <int16> WindowSizeY               |
		--------------------------------------------------------------------------------------------------
		|            <int16> WindowOriginX             |              <int16> WindowOriginY              |
		--------------------------------------------------------------------------------------------------
		|                                           Unused1                                              |
		--------------------------------------------------------------------------------------------------
		|                                           Unused2                                              |
		--------------------------------------------------------------------------------------------------
		|                                      <u_int32> FontSize                                        |
		--------------------------------------------------------------------------------------------------
		|                                     <u_int32> FontFamily                                       |
		--------------------------------------------------------------------------------------------------
		|                                     <u_int32> FontWeight                                       |
		--------------------------------------------------------------------------------------------------
		|                                    <unicode_str> Face Name                                     |
		|                                            64 B                                                |
		--------------------------------------------------------------------------------------------------
		|                                     <u_int32> CursorSize                                       |
		--------------------------------------------------------------------------------------------------
		|                                     <u_int32> FullScreen                                       |
		--------------------------------------------------------------------------------------------------
		|                                      <u_int32> QuickEdit                                       |
		--------------------------------------------------------------------------------------------------
		|                                     <u_int32> InsertMode                                       |
		--------------------------------------------------------------------------------------------------
		|                                    <u_int32> AutoPosition                                      |
		--------------------------------------------------------------------------------------------------
		|                                 <u_int32> HistoryBufferSize                                    |
		--------------------------------------------------------------------------------------------------
		|                               <u_int32> NumberOfHistoryBuffers                                 |
		--------------------------------------------------------------------------------------------------
		|                                   <u_int32> HistoryNoDup                                       |
		--------------------------------------------------------------------------------------------------
		|                                <vector<u_int32>> ColorTable                                    |
		|                                            64 B                                                |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'] = {}
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK']['size'] = size
		# 16b
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'FillAttributes'] = struct.unpack('<I', self.indata[index + 8: index + 10])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'PopupFillAttributes'] = struct.unpack('<I', self.indata[index + 10: index + 12])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'ScreenBufferSizeX'] = struct.unpack('<i', self.indata[index + 12: index + 14])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'ScreenBufferSizeY'] = struct.unpack('<i', self.indata[index + 14: index + 16])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'WindowSizeX'] = struct.unpack('<i', self.indata[index + 16: index + 18])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'WindowSizeY'] = struct.unpack('<i', self.indata[index + 18: index + 20])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'WindowOriginX'] = struct.unpack('<i', self.indata[index + 20: index + 22])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'WindowOriginY'] = struct.unpack('<i', self.indata[index + 22: index + 24])[0]
		# Bytes 24-28 & 28-32 are unused
		# 32b
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'FontSize'] = struct.unpack('<I', self.indata[index + 32: index + 36])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'FontFamily'] = struct.unpack('<I', self.indata[index + 36: index + 40])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'FontWeight'] = struct.unpack('<I', self.indata[index + 40: index + 44])[0]
		# 64b
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'Face'] = self.clean_line(self.indata[index + 44: index + 108])
		# 32b
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'CursorSize'] = struct.unpack('<I', self.indata[index + 108: index + 112])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'FullScreen'] = struct.unpack('<I', self.indata[index + 112: index + 116])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'QuickEdit'] = struct.unpack('<I', self.indata[index + 116: index + 120])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'InsertMode'] = struct.unpack('<I', self.indata[index + 120: index + 124])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'AutoPosition'] = struct.unpack('<I', self.indata[index + 124: index + 128])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'HistoryBufferSize'] = struct.unpack('<I', self.indata[index + 128: index + 132])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'NumberOfHistoryBuffers'] = struct.unpack('<I', self.indata[index + 132: index + 136])[0]
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'HistoryNoDup'] = struct.unpack('<I', self.indata[index + 136: index + 140])[0]
		# 64b
		self.extraBlocks['CONSOLE_PROPERTIES_BLOCK'][
			'ColorTable'] = struct.unpack('<I', self.indata[index + 140: index + 144])[0]


	def parse_distributedTracker_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x00000060                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000003                              |
		--------------------------------------------------------------------------------------------------
		|                                      <u_int32> Length                                          |
		--------------------------------------------------------------------------------------------------
		|                                      <u_int32> Version                                         |
		--------------------------------------------------------------------------------------------------
		|                                       <str> MachineID                                          |
		|                                             16 B                                               |
		--------------------------------------------------------------------------------------------------
		|                                    <GUID> DroidVolumeId                                        |
		|                                             16 B                                               |
		--------------------------------------------------------------------------------------------------
		|                                     <GUID> DroidFileId                                         |
		|                                             16 B                                               |
		--------------------------------------------------------------------------------------------------
		|                                  <GUID> DroidBirthVolumeId                                     |
		|                                             16 B                                               |
		--------------------------------------------------------------------------------------------------
		|                                   <GUID> DroidBirthFileId                                      |
		|                                             16 B                                               |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK'] = {}
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK']['size'] = size
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK']['length'] = \
			struct.unpack('<I', self.indata[index + 8: index + 12])[0]
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK']['version'] = \
			struct.unpack('<I', self.indata[index + 12: index + 16])[0]
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK'][
			'machine_identifier'] = self.clean_line(self.indata[index + 16: index + 32])
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK'][
			'droid_volume_identifier'] = self.indata[index + 32: index + 48].hex()
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK'][
			'droid_file_identifier'] = self.indata[index + 48: index + 64].hex()
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK'][
			'birth_droid_volume_identifier'] = self.indata[index + 64: index + 80].hex()
		self.extraBlocks['DISTRIBUTED_LINK_TRACKER_BLOCK'][
			'birth_droid_file_identifier'] = self.indata[index + 80: index + 96].hex()


	def parse_codepage_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x0000000C                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000004                              |
		--------------------------------------------------------------------------------------------------
		|                                     <u_int32> CodePage                                         |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['CONSOLE_CODEPAGE_BLOCK'] = {}
		self.extraBlocks['CONSOLE_CODEPAGE_BLOCK']['size'] = size
		self.extraBlocks['CONSOLE_CODEPAGE_BLOCK']['CodePage'] = struct.unpack('<I', self.indata[index + 8: index + 12])[0]


	def parse_specialFolder_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x00000010                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000005                              |
		--------------------------------------------------------------------------------------------------
		|                                   <u_int32> SpecialFolderID                                    |
		--------------------------------------------------------------------------------------------------
		|                                         <u_int32> Offset                                       |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['SPECIAL_FOLDER_LOCATION_BLOCK'] = {}
		self.extraBlocks['SPECIAL_FOLDER_LOCATION_BLOCK']['size'] = size
		self.extraBlocks['SPECIAL_FOLDER_LOCATION_BLOCK']['SpecialFolderID'] = struct.unpack('<I', self.indata[index + 8: index + 12])[0]
		self.extraBlocks['SPECIAL_FOLDER_LOCATION_BLOCK']['Offset'] = struct.unpack('<I', self.indata[index + 12: index + 16])[0]


	def parse_darwin_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x00000314                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000006                              |
		--------------------------------------------------------------------------------------------------
		|                                    <str> DarwinDataAnsi                                        |
		|                                           260 B                                                |
		--------------------------------------------------------------------------------------------------
		|                               <unicode_str> DarwinDataUnicode                                  |
		|                                           520 B                                                |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['DARWIN_BLOCK'] = {}
		self.extraBlocks['DARWIN_BLOCK']['size'] = size
		self.extraBlocks['DARWIN_BLOCK']['DarwinDataAnsi'] = self.read_string(index + 8)
		self.extraBlocks['DARWIN_BLOCK']['DarwinDataUnicode'] = self.read_unicode_string(index + 268)


	def parse_icon_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x00000314                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000007                              |
		--------------------------------------------------------------------------------------------------
		|                                      <str> TargetAnsi                                          |
		|                                           260 B                                                |
		--------------------------------------------------------------------------------------------------
		|                                <unicode_str> TargetUnicode                                     |
		|                                           520 B                                                |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['ICON_LOCATION_BLOCK'] = {}
		self.extraBlocks['ICON_LOCATION_BLOCK']['size'] = size
		self.extraBlocks['ICON_LOCATION_BLOCK']['TargetAnsi'] = self.read_string(index + 8)
		self.extraBlocks['ICON_LOCATION_BLOCK']['TargetUnicode'] = self.read_unicode_string(index + 268)


	def parse_shimLayer_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize >= 0x00000088                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000008                              |
		--------------------------------------------------------------------------------------------------
		|                                    <unicode_str> LayerName                                     |
		|                                            ? B                                                 |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['SHIM_LAYER_BLOCK'] = {}
		self.extraBlocks['SHIM_LAYER_BLOCK']['size'] = size
		self.extraBlocks['SHIM_LAYER_BLOCK']['LayerName'] = self.read_unicode_string(index + 8)


	def parse_metadata_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize >= 0x0000000C                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA0000009                              |
		--------------------------------------------------------------------------------------------------
		|                                    <u_int32> StorageSize                                       |
		--------------------------------------------------------------------------------------------------
		|                                    Version == 0x53505331                                       |
		--------------------------------------------------------------------------------------------------
		|                                      <GUID> FormatID                                           |
		|                                            16 B                                                |
		--------------------------------------------------------------------------------------------------
		|                   <vector<MS_OLEPS>> SerializedPropertyValue (see MS-OLEPS)                    |
		|                                             ? B                                                |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['METADATA_PRPERTIES_BLOCK'] = {}
		self.extraBlocks['METADATA_PRPERTIES_BLOCK']['size'] = size
		self.extraBlocks['METADATA_PRPERTIES_BLOCK']['StorageSize'] = struct.unpack('<I', self.indata[index + 8: index + 12])[0]
		self.extraBlocks['METADATA_PRPERTIES_BLOCK']['Version'] = hex(struct.unpack('<I', self.indata[index + 12: index + 16])[0])
		self.extraBlocks['METADATA_PRPERTIES_BLOCK']['FormatID'] = self.indata[index + 16: index + 32].hex()
		if self.extraBlocks['METADATA_PRPERTIES_BLOCK']['FormatID'].upper() == 'D5CDD5052E9C101B939708002B2CF9AE':
			# Serialized Property Value (String Name)
			index += 32
			result = []
			while True:
				value = {}
				value['ValueSize'] = struct.unpack('<I', self.indata[index: index + 4])[0]
				if hex(value['ValueSize']) == hex(0x0):
					break
				value['NameSize'] = struct.unpack('<I', self.indata[index + 4: index + 8])[0]
				value['Name'] = self.read_unicode_string(index + 8)
				value['Value'] = '' # TODO MS-OLEPS

				result.append(value)
				index += 4 + 4 + 2 + value['NameSize'] + value['ValueSize']

			self.extraBlocks['METADATA_PRPERTIES_BLOCK']['SerializedPropertyValueString'] = result
		else:
			# Serialized Property Value (Integer Name)
			try:
				index += 32
				result = []
				while True:
					value = {}
					value['ValueSize'] = struct.unpack('<I', self.indata[index: index + 4])[0]
					if hex(value['ValueSize']) == hex(0x0):
						break
					value['Id'] = struct.unpack('<I', self.indata[index + 4: index + 8])[0]
					value['Value'] = '' # TODO MS-OLEPS

					result.append(value)
					index += value['ValueSize']

				self.extraBlocks['METADATA_PRPERTIES_BLOCK']['SerializedPropertyValueInteger'] = result
			except Exception as e:
				print(e)


	def parse_knownFolder_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize == 0x0000001C                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA000000B                              |
		--------------------------------------------------------------------------------------------------
		|                                     <GUID> KnownFolderID                                       |
		|                                            16 B                                                |
		--------------------------------------------------------------------------------------------------
		|                                       <u_int32> Offset                                         |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['KNOWN_FOLDER_LOCATION_BLOCK'] = {}
		self.extraBlocks['KNOWN_FOLDER_LOCATION_BLOCK']['size'] = size
		self.extraBlocks['KNOWN_FOLDER_LOCATION_BLOCK']['KnownFolderID'] = self.indata[index + 8: index + 24].hex()
		self.extraBlocks['KNOWN_FOLDER_LOCATION_BLOCK']['Offset'] = struct.unpack('<I', self.indata[index + 24: index + 28])[0]


	def parse_shellItem_block(self, index, size):
		"""
		--------------------------------------------------------------------------------------------------
		|         0-7b         |         8-15b         |         16-23b         |         24-31b         |
		--------------------------------------------------------------------------------------------------
		|                              <u_int32> BlockSize >= 0x0000000A                                 |
		--------------------------------------------------------------------------------------------------
		|                            <u_int32> BlockSignature == 0xA000000C                              |
		--------------------------------------------------------------------------------------------------
		|                                       <IDList> IDList                                          |
		--------------------------------------------------------------------------------------------------
		"""
		self.extraBlocks['SHELL_ITEM_IDENTIFIER_BLOCK'] = {}
		self.extraBlocks['SHELL_ITEM_IDENTIFIER_BLOCK']['size'] = size
		self.extraBlocks['SHELL_ITEM_IDENTIFIER_BLOCK']['IDList'] = '' # TODO


	def print_lnk_file(self):
		print('Windows Shortcut Information:')
		print('\tLink Flags: %s - (%s)' % (self.format_linkFlags(), self.lnk_header['rlinkFlags']))
		print('\tFile Flags: %s - (%s)' % (self.format_fileFlags(), self.lnk_header['rfileFlags']))
		print('')
		try:
			print('\tCreation Timestamp: %s' % (self.ms_time_to_unix_time(self.lnk_header['creation_time'])))
			print('\tModified Timestamp: %s' % (self.ms_time_to_unix_time(self.lnk_header['modified_time'])))
			print('\tAccessed Timestamp: %s' % (self.ms_time_to_unix_time(self.lnk_header['accessed_time'])))
			print('')
		except:
			print('\tProblem Parsing Timestamps')
		print(
			'\tFile Size: %s (r: %s)' % (str(self.lnk_header['file_size']), str(len(self.indata))))
		print('\tIcon Index: %s ' % (str(self.lnk_header['icon_index'])))
		print('\tWindow Style: %s ' % (str(self.lnk_header['windowstyle'])))
		print('\tHotKey: %s ' % (str(self.lnk_header['hotkey'])))

		print('')

		for rline in self.data:
			print('\t%s: %s' % (rline, self.data[rline]))

		print('')
		print('\tEXTRA BLOCKS:')
		for enabled in self.extraBlocks:
			print('\t\t%s' % enabled)
			for block in self.extraBlocks[enabled]:
				print('\t\t\t[%s] %s' % (block, self.extraBlocks[enabled][block]))


	def ms_time_to_unix_time(self, time):
		return datetime.datetime.fromtimestamp(time / 10000000.0 - 11644473600).strftime('%Y-%m-%d %H:%M:%S')


	def read_string(self, index):
		result = ''
		while self.indata[index] != 0x00:
			result += chr(self.indata[index])
			index += 1
		return result


	def read_unicode_string(self, index):
		begin = end = index
		while self.indata[index] != 0x00:
			end += 1
			index += 1
		return self.clean_line(self.indata[begin: end].replace(b'\x00', b''))


	def read_stringData(self, index, u_mult):
		string_size = struct.unpack('<H', self.indata[index: index + 2])[0] * u_mult
		string = self.clean_line(self.indata[index + 2: index + 2 + string_size].replace(b'\x00', b''))
		new_index = index + string_size + 2
		return new_index, string


	@staticmethod
	def enabled_flags_to_list(flags):
		enabled = []
		for flag in flags:
			if flags[flag]:
				enabled.append(flag)
		return enabled


	def format_linkFlags(self):
		enabled = self.enabled_flags_to_list(self.linkFlag)
		return ' | '.join(enabled)


	def format_fileFlags(self):
		enabled = self.enabled_flags_to_list(self.fileFlag)
		return ' | '.join(enabled)


	def print_short(self, pjson=False):
		out = ''
		if self.linkFlag['HasRelativePath']:
			out += self.data['relativePath']
		if self.linkFlag['HasArguments']:
			out += ' ' + self.data['commandLineArguments']

		if pjson:
			print(json.dumps({'command': out}))
		else:
			print(out)


	def print_json(self, print_all=False):
		res = self.get_json(print_all)
		print(json.dumps(res, indent=4, separators=(',', ': ')))


	def get_json(self, get_all=False):
		res = {'header': self.lnk_header, 'data': self.data, 'target': self.targets, 'link_info': self.loc_information, 'extra': self.extraBlocks}

		if 'creation_time' in res['header']:
			res['header']['creation_time'] = self.ms_time_to_unix_time(res['header']['creation_time'])
		if 'accessed_time' in res['header']:
			res['header']['accessed_time'] = self.ms_time_to_unix_time(res['header']['accessed_time'])
		if 'modified_time' in res['header']:
			res['header']['modified_time'] = self.ms_time_to_unix_time(res['header']['modified_time'])

		if not get_all:
			res['header'].pop('header_size', None)
			res['header'].pop('reserved0', None)
			res['header'].pop('reserved1', None)
			res['header'].pop('reserved2', None)
			res['target'].pop('size', None)
			res['link_info'].pop('LinkInfoSize', None)
			res['link_info'].pop('LinkInfoHeaderSize', None)
			res['link_info'].pop('VolumeIDOffset', None)
			res['link_info'].pop('LocalBasePathOffset', None)
			res['link_info'].pop('CommonNetworkRelativeLinkOffset', None)
			res['link_info'].pop('CommonPathSuffixOffset', None)
			if 'VolumeIDAndLocalBasePath' in res['link_info']:
				res['link_info']['location_info'].pop('VolumeIDSize', None)
				res['link_info']['location_info'].pop('VolumeLabelOffset', None)
			if 'CommonNetworkRelativeLinkAndPathSuffix' in res['link_info']:
				res['link_info']['location_info'].pop('CommonNetworkRelativeLinkSize', None)
				res['link_info']['location_info'].pop('NetNameOffset', None)
				res['link_info']['location_info'].pop('DeviceNameOffset', None)

		return res


def test_case(filename):
	with open(filename, 'rb') as file:
		tmp = lnk_file(fhandle=file, debug=True)
		tmp.print_lnk_file()
		# tmp.print_short(True)
		# tmp.print_json()


def main():
	arg_parser = argparse.ArgumentParser(description=__description__)
	arg_parser.add_argument('-f', '--file', dest='file', required=True,
							help='absolute or relative path to the file')
	arg_parser.add_argument('-j', '--json', action='store_true',
							help='print output in JSON')
	arg_parser.add_argument('-d', '--json_debug', action='store_true',
							help='print all extracted data in JSON (i.e. offsets and sizes)')
	arg_parser.add_argument('-D', '--debug', action='store_true',
							help='print debug info')
	args = arg_parser.parse_args()

	with open(args.file, 'rb') as file:
		lnk = lnk_file(fhandle=file, debug=args.debug)
		if args.json:
			lnk.print_json(args.json_debug)
		else:
			lnk.print_lnk_file()


if __name__ == '__main__':
	main()
