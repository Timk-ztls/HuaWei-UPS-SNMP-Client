from snmp_connet import get_formatted_snmp_output
import time

# 如果是三相电需要修改snmp_connet中的部分参数，如单位 小数点与表留信息自行添加B C相设置
target_ip = ''
community_string = 'snmpread0'
object_name = 'hwUpsMIB'

while True:
    start_time = time.time()  # 记录开始时间
    formatted_dict_outputs = get_formatted_snmp_output(target_ip, community_string, object_name)
    for output_dict in formatted_dict_outputs:
        if output_dict['name'] == 'hwUpsInputVoltageA':
            # 移除尾部的 'V' 并转换为整数
            hwUpsInputVoltageA_value = int(float(output_dict['value'].rstrip('V')))
        elif output_dict['name'] == 'hwUpsBatteryBackupTime':
            # 移除尾部的 'min' 并保留整数
            hwUpsBatteryBackupTime_value = int(output_dict['value'].rstrip('min'))
    # 进行条件判断
    print("当前电压:"+str(hwUpsInputVoltageA_value)+'V  '+"当前电池剩余时间"+str(hwUpsBatteryBackupTime_value)+'min')
    if hwUpsInputVoltageA_value == 0 and hwUpsBatteryBackupTime_value <= 10:
        print("当前电压与电池剩余时间异常  当前电压:" + str(hwUpsInputVoltageA_value) + 'V  ' + "当前电池剩余时间" + str(
            hwUpsBatteryBackupTime_value) + 'min')
        # 执行特定命令
    else:
        # 如果不满足条件，则继续循环或执行其他逻辑
        pass
    end_time = time.time()  # 记录结束时间
    execution_time = end_time - start_time  # 计算执行时间
    print(f"本次执行时间：{round(execution_time, 2)}秒")
    time.sleep(15)
