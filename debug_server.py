#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试服务器 - 最简单的HTTP服务器"""

import sys
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# 确保可以导入main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import main
    print("✓ main导入成功")
except Exception as e:
    print(f"✗ main导入失败: {e}")
    sys.exit(1)

# 全局计算器实例
calc = None

try:
    print("正在初始化计算器...")
    calc = main.TieBanCalculator()
    print("✓ 计算器初始化成功")
except Exception as e:
    print(f"✗ 计算器初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

class DebugHandler(BaseHTTPRequestHandler):
    """调试请求处理器"""
    
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def do_GET(self):
        """GET请求 - 提供静态文件"""
        try:
            if self.path == '/':
                self.path = '/index.html'
            
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.path.lstrip('/'))
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                self.send_response(404)
                self.end_headers()
                return
            
            content_type = 'text/html'
            if self.path.endswith('.css'):
                content_type = 'text/css'
            elif self.path.endswith('.js'):
                content_type = 'application/javascript'
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.end_headers()
            self.wfile.write(content)
            return
        except Exception as e:
            print(f"GET请求错误: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
    
    def do_POST(self):
        """POST请求 - 处理计算"""
        try:
            print(f"\n{'='*60}")
            print(f"收到POST请求: {self.path}")
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            print(f"请求数据长度: {len(post_data)} 字节")
            
            data = json.loads(post_data.decode('utf-8'))
            print(f"解析后的数据:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            
            if self.path == '/api/calculate':
                print(f"\n开始计算...")
                
                # 解析参数
                gender = data.get('gender', '男')
                
                birth = data.get('birth', {})
                dt_birth = datetime(
                    int(birth.get('year', 1990)),
                    int(birth.get('month', 1)),
                    int(birth.get('day', 1)),
                    int(birth.get('hour', 12)),
                    int(birth.get('minute', 0))
                )
                
                query = data.get('query', {})
                dt_query = datetime(
                    int(query.get('year', datetime.now().year)),
                    int(query.get('month', datetime.now().month)),
                    int(query.get('day', datetime.now().day)),
                    int(query.get('hour', datetime.now().hour)),
                    int(query.get('minute', datetime.now().minute))
                )
                
                print(f"出生日期: {dt_birth}")
                print(f"求测日期: {dt_query}")
                print(f"性别: {gender}")
                
                # 转换为八字
                info_b = main.convert_to_bazi_info(dt_birth)
                info_q = main.convert_to_bazi_info(dt_query)
                
                if not info_b or not info_q:
                    print("✗ 八字转换失败")
                    response = {'success': False, 'error': '八字转换失败'}
                else:
                    # 执行计算
                    print("调用 calc.calculate()...")
                    result = calc.calculate({
                        'birth_info': info_b,
                        'query_info': info_q,
                        'gender': gender
                    })
                    print(f"✓ 计算完成")
                    
                    response = {
                        'success': True,
                        'info_b': info_b,
                        'info_q': info_q,
                        'gender': gender,
                        'result': result
                    }
                
                print(f"\n准备发送响应...")
                self._set_headers(200)
                json_str = json.dumps(response, ensure_ascii=False)
                print(f"响应长度: {len(json_str)} 字符")
                self.wfile.write(json_str.encode('utf-8'))
                print(f"✓ 响应已发送")
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            print(f"\n✗ POST请求错误: {e}")
            import traceback
            traceback.print_exc()
            self._set_headers(500)
            error_response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        """重写日志方法，不输出默认日志"""
        pass

def run_debug_server():
    """运行调试服务器"""
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, DebugHandler)
    print("="*60)
    print("  调试服务器已启动")
    print("="*60)
    print(f"\n服务器地址: http://localhost:8000")
    print(f"\n请在浏览器中打开上述地址开始使用")
    print(f"\n按 Ctrl+C 停止服务器\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        httpd.shutdown()

if __name__ == "__main__":
    run_debug_server()
