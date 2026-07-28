#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试六亲考刻功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import TieBanSuan, LunarSolarConverter

def test_six_qin():
    print("="*80)
    print("  测试六亲考刻功能")
    print("="*80)
    
    # 初始化系统
    tb = TieBanSuan()
    print("\n✓ 系统初始化成功")
    
    # 模拟用户输入：2026年5月17日，卯时6时38分
    converter = LunarSolarConverter()
    
    birth_info = {
        'date_str': '2026-05-17 06:38',
        'lunar_month': 4,
        'lunar_day': 1,
        'lunar_str': '农历二〇二六年四月初一',
        'is_leap': False,
        'bazi': {
            'year': ('丙', '午'),
            'month': ('癸', '巳'),
            'day': ('辛', '卯'),
            'time': ('辛', '卯')
        }
    }
    
    query_info = {
        'date_str': '2026-05-17',
        'bazi': {
            'year': ('丙', '午'),
            'month': ('癸', '巳'),
            'day': ('辛', '卯'),
            'time': ('辛', '卯')
        }
    }
    
    payload = {
        'birth_info': birth_info,
        'query_info': query_info,
        'gender': '男',
        'six_qin_info': {
            '父母': '属猴'
        }
    }
    
    print(f"\n测试输入:")
    print(f"  出生时间: {birth_info['date_str']}")
    print(f"  性别: {payload['gender']}")
    print(f"  六亲信息: {payload.get('six_qin_info', {})}")
    
    try:
        print("\n开始计算...")
        result = tb.calculate(payload)
        print("\n✓ 计算成功!")
        
        print("\n" + "="*80)
        print("  计算结果摘要")
        print("="*80)
        
        print(f"\n【基础信息】")
        print(f"  {result['header_info']}")
        print(f"  {result['cong_calc']}")
        print(f"  {result['moment_calc']}")
        print(f"  {result['main_calc']}")
        
        print(f"\n【六亲考刻分析】")
        if 'six_qin_analysis' in result:
            analysis = result['six_qin_analysis']
            print(f"  终局条文数: {analysis['final_fortune']}")
            print(f"  终局断语: {analysis['final_duanyu']}")
            print(f"  对应年龄: {analysis['final_age']}")
            
            print(f"\n  各六亲分析:")
            for qin_type, qin_data in analysis['qin_analysis'].items():
                print(f"    {qin_type}:")
                if qin_data['fortune']:
                    fort = qin_data['fortune']
                    print(f"      - 条文: {fort['num']}")
                    print(f"      - 断语: {fort['duanyu']}")
                    print(f"      - 年龄: {fort['age']}")
                    print(f"      - 差异: {qin_data['closest_diff']}")
                else:
                    print(f"      - 未找到对应条文")
        
        print(f"\n【六亲验证结果】")
        if 'six_qin_verify' in result:
            verify = result['six_qin_verify']
            print(f"  已知信息: {verify['known_info']}")
            print(f"  推荐刻别: {verify['verified_kebie']}")
            print(f"  匹配分数: {verify['match_scores']}")
        
        print("\n" + "="*80)
        print("  ✓ 测试完成，六亲考刻功能正常!")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ 出错了!")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")
        import traceback
        traceback.print_exc()
        
        return False
    
    return True

if __name__ == "__main__":
    success = test_six_qin()
    sys.exit(0 if success else 1)
