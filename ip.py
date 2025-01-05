import socket
import requests
import geoip2.database
import os
import sys
from dotenv import load_dotenv

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def is_valid_ip(ip):
    """验证IP地址格式是否有效"""
    try:
        # 移除IPv6的方括号
        ip = ip.strip('[]')
        # 分割IP地址
        parts = ip.split('.')
        # 检查IPv4格式
        if len(parts) != 4:
            return False
        # 检查每个部分是否在0-255范围内
        return all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, AttributeError):
        return False

def download_mmdb():
    """下载MaxMind GeoIP2数据库"""
    try:
        data_dir = "data"
        ensure_dir(data_dir)
        
        url = "https://raw.githubusercontent.com/Loyalsoldier/geoip/release/GeoLite2-Country.mmdb"
        response = requests.get(url)
        
        db_path = os.path.join(data_dir, "GeoLite2-Country.mmdb")
        with open(db_path, "wb") as f:
            f.write(response.content)
        print("GeoIP2数据库更新成功")
        return db_path
    except Exception as e:
        print(f"下载GeoIP2数据库失败: {str(e)}")
        sys.exit(1)

def get_country_code(ip, reader):
    """查询IP所属国家代码"""
    try:
        response = reader.country(ip)
        return response.country.iso_code or "XX"
    except Exception:
        return "XX"

def resolve_domain(reader):
    """解析域名获取IP"""
    try:
        # 检查必需的环境变量
        if 'TARGET_DOMAIN' not in os.environ:
            print('错误：未设置 TARGET_DOMAIN 环境变量')
            return []
            
        domain = os.environ['TARGET_DOMAIN']
        ports = os.environ.get('TARGET_PORTS', '443').split(',')
        ports = [port.strip() for port in ports if port.strip().isdigit()]
        
        if not ports:
            print('警告：未设置有效的 TARGET_PORTS 环境变量，使用默认端口443')
            ports = ['443']
        
        print(f"\n[域名解析] 正在解析域名: {domain}")
        addrinfo = socket.getaddrinfo(domain, None)
        all_ips = set()
        
        for addr in addrinfo:
            ip = addr[4][0]
            if ':' in ip:
                all_ips.add(f'[{ip}]')
            else:
                all_ips.add(ip)
        
        results = []
        for ip in sorted(all_ips):
            country_code = get_country_code(ip.strip('[]'), reader)
            for port in ports:
                result = f'{ip}:{port}#{country_code}'
                results.append(result)
                print(f"[域名解析] {result}")
                
        return results
            
    except socket.gaierror as e:
        print(f'DNS解析错误: {str(e)}')
        return []
    except Exception as e:
        print(f'域名解析发生错误: {str(e)}')
        return []

def read_ip_from_url(reader):
    """从GitHub URL读取IP列表并查询国家代码"""
    try:
        url = "https://raw.githubusercontent.com/rdone4425/youxuanyuming/refs/heads/main/ip.txt"
        print(f"\n[URL读取] 正在从GitHub获取IP列表...")
        
        response = requests.get(url)
        response.raise_for_status()
        
        ip_list = response.text.strip().split()
        results = []
        
        for ip in ip_list:
            ip = ip.strip()
            if not ip:
                continue
            
            # 移除IP验证，直接获取国家代码    
            country_code = get_country_code(ip, reader)
            result = f'{ip}#{country_code}'
            results.append(result)
            print(f"[URL读取] {result}")
                
        return results
            
    except requests.RequestException as e:
        print(f'获取GitHub IP列表失败: {str(e)}')
        return []
    except Exception as e:
        print(f'URL读取发生错误: {str(e)}')
        return []

def main():
    """主函数，自动检测条件并执行"""
    print("正在初始化...")
    
    # 加载环境变量
    if not os.environ.get('GITHUB_ACTIONS'):
        load_dotenv()
    
    # 检查条件
    has_domain = 'TARGET_DOMAIN' in os.environ
    
    # 严格检查环境变量
    if has_domain and 'TARGET_DOMAIN' not in os.environ:
        print('错误：未设置 TARGET_DOMAIN 环境变量')
        has_domain = False
    
    if not has_domain:
        print("提示：未设置域名环境变量，将只从GitHub获取IP列表")
    
    # 准备GeoIP2数据库
    db_path = os.path.join("data", "GeoLite2-Country.mmdb")
    if not os.path.exists(db_path):
        db_path = download_mmdb()
    
    reader = geoip2.database.Reader(db_path)
    all_results = []
    
    try:
        # 执行域名解析
        if has_domain:
            if 'TARGET_DOMAIN' not in os.environ:
                print('错误：未设置 TARGET_DOMAIN 环境变量')
            else:
                domain_results = resolve_domain(reader)
                all_results.extend(domain_results)
        
        # 从GitHub读取IP列表
        url_results = read_ip_from_url(reader)
        all_results.extend(url_results)
        
        # 保存所有结果到一个文件
        if all_results:
            with open('ip.txt', 'w', encoding='utf-8') as f:
                for result in all_results:
                    f.write(f'{result}\n')
        
    finally:
        reader.close()
    
    print("\n处理完成！")
    print("所有结果已保存到 ip.txt")

if __name__ == '__main__':
    main()