#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""铁板神数HTTP服务器 - 修复版"""

import os
import sys
import json
import traceback
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# 确保可以导入main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import main
    from main import TieBanCalculator, convert_to_bazi_info
except ImportError as e:
    print(f"【错误】无法导入main.py: {e}")
    sys.exit(1)

# 全局计算器实例（避免重复加载数据库）
_calculator = None
_calculator_lock = False

def get_calculator():
    """获取计算器实例（带锁防止并发问题）"""
    global _calculator, _calculator_lock
    
    if _calculator is None and not _calculator_lock:
        _calculator_lock = True
        print(">>> 正在初始化计算器（首次加载数据库）...")
        try:
            _calculator = TieBanCalculator()
            print(">>> 计算器初始化完成")
        finally:
            _calculator_lock = False
    
    while _calculator is None and _calculator_lock:
        import time
        time.sleep(0.1)
    
    return _calculator

class TBServer(BaseHTTPRequestHandler):
    """铁板神数HTTP请求处理器"""

    def _set_headers(self, content_type='text/html', status_code=200):
        """设置响应头"""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        """处理OPTIONS请求"""
        self._set_headers()

    def do_GET(self):
        """处理GET请求 - 提供静态文件"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # 默认返回index.html
        if path == '/' or path == '':
            path = '/index.html'

        # 安全检查
        if '..' in path:
            self._send_error(403, "禁止访问")
            return

        # 提供静态文件
        try:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path.lstrip('/'))

            if not os.path.exists(file_path):
                self._send_error(404, f"文件不存在: {path}")
                return

            # 设置Content-Type
            content_type = 'text/html'
            if path.endswith('.css'):
                content_type = 'text/css'
            elif path.endswith('.js'):
                content_type = 'application/javascript'

            with open(file_path, 'rb') as f:
                content = f.read()

            self._set_headers(content_type)
            self.wfile.write(content)

        except Exception as e:
            print(f"提供静态文件时出错: {e}")
            self._send_error(500, str(e))

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            if parsed_path.path == '/api/calculate':
                self._handle_calculate(post_data)
            else:
                self._send_error(404, "API接口不存在")

        except Exception as e:
            print(f"处理POST请求时出错: {e}")
            traceback.print_exc()
            self._send_error(500, str(e))

    def _send_error(self, status_code, message):
        """发送错误响应"""
        print(f"错误: {status_code} - {message}")
        self._set_headers('application/json', status_code)
        response = json.dumps({'success': False, 'error': message}, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))

    def _handle_calculate(self, post_data):
        """处理排盘计算"""
        try:
            print(">>> 收到排盘请求")

            # 解析数据
            data = json.loads(post_data.decode('utf-8'))
            gender = data.get('gender', '男')
            six_qin_info = data.get('six_qin_info', {})

            birth = data.get('birth', {})
            dt_birth = datetime.datetime(
                int(birth.get('year', 1990)),
                int(birth.get('month', 1)),
                int(birth.get('day', 1)),
                int(birth.get('hour', 12)),
                int(birth.get('minute', 0))
            )

            query = data.get('query', {})
            dt_query = datetime.datetime(
                int(query.get('year', datetime.datetime.now().year)),
                int(query.get('month', datetime.datetime.now().month)),
                int(query.get('day', datetime.datetime.now().day)),
                int(query.get('hour', datetime.datetime.now().hour)),
                int(query.get('minute', datetime.datetime.now().minute))
            )

            print(f">>> 时间解析完成")
            print(f">>> 六亲信息: {six_qin_info}")

            # 转换为八字
            info_b = convert_to_bazi_info(dt_birth)
            info_q = convert_to_bazi_info(dt_query)

            if not info_b or not info_q:
                self._send_error(400, "八字转换失败")
                return

            print(f">>> 八字转换完成")

            # 获取计算器实例
            print(f">>> 获取计算器...")
            calc = get_calculator()
            if calc is None:
                self._send_error(500, "计算器初始化失败")
                return
            print(f">>> 开始排盘...")

            # 执行计算
            result = calc.calculate({
                'birth_info': info_b,
                'query_info': info_q,
                'gender': gender,
                'six_qin_info': six_qin_info
            })
            print(f">>> 排盘完成，正在准备响应...")
            
            # 清理结果，确保只包含可JSON序列化的内容
            def clean(obj):
                if isinstance(obj, dict):
                    return {k: clean(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean(x) for x in obj]
                elif isinstance(obj, (int, float, str, bool)) or obj is None:
                    return obj
                else:
                    return str(obj)
            
            cleaned_result = clean(result)
            
            # 返回结果
            response = {
                'success': True,
                'info_b': info_b,
                'info_q': info_q,
                'gender': gender,
                'result': cleaned_result
            }

            print(f">>> 正在发送响应...")
            self._set_headers('application/json')
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            print(f">>> 响应已发送")

        except Exception as e:
            print(f"排盘错误: {e}")
            tb_str = traceback.format_exc()
            print(tb_str)
            self._send_error(500, f"计算失败: {str(e)}")

    def log_message(self, format, *args):
        """重写日志方法"""
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server(host='localhost', port=8000):
    """运行服务器"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, TBServer)

    print("="*60)
    print("  铁板神数HTTP服务器")
    print("="*60)
    print(f"\n服务器地址: http://{host}:{port}")
    print(f"\n请在浏览器中打开上述地址开始使用")
    print("\n按 Ctrl+C 停止服务器\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()
