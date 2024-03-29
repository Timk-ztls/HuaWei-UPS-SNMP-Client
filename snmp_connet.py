from pysnmp.hlapi import *
from pysnmp.smi import builder, view, compiler

# 假设单位信息
units_mapping = {
	'hwUpsInputVoltageA': 'V',
	'hwUpsDeviceTemperature': '°C',
	'hwUpsInputFrequency': 'Hz',
	'hwUpsOutputVoltageA': 'V',
	'hwUpsOutputCurrentA': 'A',
	'hwUpsOutputFrequency': 'Hz',
	'hwUpsOutputActivePowerA': 'kW',
	'hwUpsOutputAppearancePowerA': 'kVA',
	'hwUpsOutputLoadA': '%',
	'hwUpsBypassInputVoltageA': 'V',
	'hwUpsBypassInputFrequency': 'Hz',
	'hwUpsBatteryVoltage': 'V',
	'hwUpsBatteryCapacityLeft': '%',
	'hwUpsBatteryBackupTime': 'min'
}

# 新增：假设除数信息，用于处理小数点和时间等
divisors_mapping = {
	'hwUpsInputVoltageA': (10, 1),
	'hwUpsDeviceTemperature': (10, 1),
	'hwUpsInputFrequency': (100, 1),
	'hwUpsOutputVoltageA': (10, 1),
	'hwUpsOutputCurrentA': (10, 1),
	'hwUpsOutputFrequency': (100, 1),
	'hwUpsOutputActivePowerA': (10, 1),
	'hwUpsOutputAppearancePowerA': (10, 1),
	'hwUpsOutputLoadA': (10, 0),
	'hwUpsBypassInputVoltageA': (10, 1),
	'hwUpsBypassInputFrequency': (100, 1),
	'hwUpsBatteryVoltage': (10, 1),
	'hwUpsBatteryBackupTime': (60, 0),
}

# 定义需要保留的对象名称列表
retain_objects = [
	'hwUpsSystemMainDeviceESN',
	'hwUpsSystemType',
	'hwUpsSysInerProtVersion',
	'hwUpsSysDeviceNum',
	'hwUpsDeviceSoftVersion',
	'hwUpsInputVoltageA',
	'hwUpsDeviceTemperature',
	'hwUpsInputFrequency',
	'hwUpsOutputVoltageA',
	'hwUpsOutputCurrentA',
	'hwUpsOutputFrequency',
	'hwUpsOutputActivePowerA',
	'hwUpsOutputAppearancePowerA',
	'hwUpsOutputLoadA',
	'hwUpsBypassInputVoltageA',
	'hwUpsBypassInputFrequency',
	'hwUpsBatteryVoltage',
	'hwUpsBatteryCapacityLeft',
	'hwUpsBatteryBackupTime',
	'hwUpsCtrlECOSwitch',
	'hwUpsCtrlModelType',
	'hwUpsCtrlInputStandard',
	'hwUpsCtrlOutputStandard',
	'hwUpsCtrlPowerOnState',
	# 在这里添加其他需要保留的对象名称
]

# 创建MIB编译器和视图控制器
mibBuilder = builder.MibBuilder()
compiler.addMibCompiler(mibBuilder, sources=['./MIB'])
mibBuilder.loadModules('HUAWEI-UPS-MIB')
mibViewController = view.MibViewController(mibBuilder)


def adjust_value_with_divisor(object_name, value):
	"""
    根据除数调整值，并考虑是否需要保留小数。
    """
	try:
		divisor, decimal_places = divisors_mapping.get(object_name, (1, 0))
		value = float(value)
		adjusted_value = value / divisor
		format_string = "{:." + str(decimal_places) + "f}"
		return format_string.format(adjusted_value)
	except ValueError:
		return value


def get_oid_from_name(object_name):
	try:
		oid = mibViewController.mibBuilder.importSymbols('HUAWEI-UPS-MIB', object_name)[0].getName()
		return oid
	except Exception as e:
		print(f"Error finding OID for {object_name}: {e}")
		return None


def snmp_walk(target_ip, community_string, object_name):
	results_with_units_and_divisors = {}
	oid = get_oid_from_name(object_name)
	if oid is None:
		return

	for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
			SnmpEngine(),
			CommunityData(community_string),
			UdpTransportTarget((target_ip, 161)),
			ContextData(),
			ObjectType(ObjectIdentity(oid)),
			lexicographicMode=False):

		if errorIndication:
			print(errorIndication)
			break
		elif errorStatus:
			print('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
			break
		else:
			for varBind in varBinds:
				oid, value = varBind
				symbol = mibViewController.getNodeLocation(oid.getOid())
				object_name = symbol[1]
				unit = units_mapping.get(object_name, '')

				adjusted_value = adjust_value_with_divisor(object_name, value.prettyPrint())
				results_with_units_and_divisors[object_name] = {'value': adjusted_value, 'unit': unit}

	# 替换命名值
	return replace_named_values(results_with_units_and_divisors)


def replace_named_values(results):
	named_values_mapping = {
		'hwUpsCtrlInputStandard': {'1': 'singlePhase', '2': 'threePhase'},
		'hwUpsCtrlOutputStandard': {'1': "singlePhase", '2': "threePhase"},
		'hwUpsCtrlPowerOnState': {'1': 'powerOff', '2': 'powerOn', '3': 'powerOnFail', '4': 'powerOnComplete'},
		'hwUpsCtrlECOSwitch': {'1': 'noECO', '2': 'eco'},
		'hwUpsCtrlPowerOn': {'1': 'powerOn', '255': 'unknown'},
		'hwUpsCtrlPowerOff': {'1': 'powerOff', '255': 'unknown'},
		'hwUpsCtrlModelType': {'17': 'model6K', '33': 'mode110K', '65': 'model20K'},
		'hwUpsCtrlBatteryEndTest': {'1': 'toEndTest', '255': 'unknown'},

	}
	for key, result in results.items():
		value = result['value']
		if key in named_values_mapping and value in named_values_mapping[key]:
			result['value'] = named_values_mapping[key][value]
	return results


def filter_results(results, retain_objects):
	"""
    过滤结果，仅保留retain_objects列表中定义的项目。
    """
	filtered_results = {key: value for key, value in results.items() if key in retain_objects}
	return filtered_results


def get_formatted_snmp_output(target_ip, community_string, object_name):
	# 执行SNMP walk操作并处理结果
	results = snmp_walk(target_ip, community_string, object_name)

	# 过滤结果，仅保留指定的项目
	filtered_results = filter_results(results, retain_objects)

	# 替换命名值
	final_results = replace_named_values(filtered_results)

	# 准备格式化输出
	formatted_dict_list = []
	for name, info in final_results.items():
		# 如果单位存在，则将值和单位拼接在一起；否则，仅使用值
		value_with_unit = f"{info['value']}{info.get('unit', '')}"

		# 构建字典
		formatted_dict = {
			"name": name,
			"value": value_with_unit  # 值和单位组合在一起
		}
		formatted_dict_list.append(formatted_dict)

	return formatted_dict_list
