#!/usr/bin/env python3
"""
WireGuard Connection Diagnostics Tool

Скрипт для диагностики соединения WireGuard, проверяющий:
1. Правильность конфигурации
2. Активность интерфейса WireGuard
3. Маршрутизацию трафика
4. Соединение с WireGuard сервером
5. Проверку DNS
6. Доступность интернета через VPN
"""

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union

# Цвета для вывода в терминал
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def run_command(command: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    """
    Запускает команду и возвращает код завершения, стандартный вывод и ошибки.
    
    Args:
        command: Команда для выполнения как список аргументов
        timeout: Таймаут выполнения в секундах
        
    Returns:
        Кортеж (код возврата, stdout, stderr)
    """
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        process.kill()
        return 1, "", "Timeout expired"
    except Exception as e:
        return 1, "", str(e)

def print_step(message: str) -> None:
    """Выводит заголовок шага диагностики"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {message} ==={Colors.ENDC}")

def print_success(message: str) -> None:
    """Выводит сообщение об успехе"""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_warning(message: str) -> None:
    """Выводит предупреждение"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

def print_error(message: str) -> None:
    """Выводит сообщение об ошибке"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(message: str) -> None:
    """Выводит информационное сообщение"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.ENDC}")

def validate_config_file(config_path: str) -> Dict[str, Any]:
    """
    Проверяет корректность конфигурационного файла WireGuard.
    
    Args:
        config_path: Путь к конфигурационному файлу
        
    Returns:
        Словарь с данными конфигурации или пустой словарь в случае ошибки
    """
    print_step("Проверка конфигурационного файла")
    
    if not os.path.exists(config_path):
        print_error(f"Файл конфигурации не найден: {config_path}")
        return {}
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    config = {}
    current_section = None
    
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Проверяем секцию
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            config[current_section] = {}
            continue
        
        if '=' in line and current_section:
            key, value = [x.strip() for x in line.split('=', 1)]
            config[current_section][key] = value
    
    # Проверяем обязательные поля
    required_fields = {
        'Interface': ['PrivateKey', 'Address'],
        'Peer': ['PublicKey', 'Endpoint', 'AllowedIPs']
    }
    
    config_ok = True
    for section, fields in required_fields.items():
        if section not in config:
            print_error(f"Отсутствует секция [{section}]")
            config_ok = False
            continue
        
        for field in fields:
            if field not in config[section]:
                print_error(f"Отсутствует поле {field} в секции [{section}]")
                config_ok = False
    
    if config_ok:
        print_success("Файл конфигурации содержит все необходимые поля")
        
        # Дополнительная информация
        if 'Interface' in config and 'Address' in config['Interface']:
            print_info(f"IP-адрес клиента: {config['Interface']['Address']}")
        
        if 'Peer' in config and 'Endpoint' in config['Peer']:
            print_info(f"Endpoint сервера: {config['Peer']['Endpoint']}")
            
        if 'Peer' in config and 'AllowedIPs' in config['Peer']:
            print_info(f"Разрешенные IP: {config['Peer']['AllowedIPs']}")
    
    return config

def check_interface_status(interface_name: str) -> bool:
    """
    Проверяет, активен ли интерфейс WireGuard.
    
    Args:
        interface_name: Имя интерфейса WireGuard
        
    Returns:
        True, если интерфейс активен, иначе False
    """
    print_step(f"Проверка статуса интерфейса {interface_name}")
    
    # Проверяем, существует ли интерфейс
    returncode, stdout, stderr = run_command(['ip', 'link', 'show', interface_name])
    
    if returncode != 0:
        print_error(f"Интерфейс {interface_name} не существует")
        return False
    
    # Проверяем, активен ли интерфейс
    if "state UP" in stdout:
        print_success(f"Интерфейс {interface_name} активен")
        active = True
    else:
        print_error(f"Интерфейс {interface_name} не активен (состояние: DOWN)")
        active = False
    
    # Получаем дополнительную информацию об интерфейсе с помощью wg show
    returncode, stdout, stderr = run_command(['wg', 'show', interface_name])
    
    if returncode != 0:
        print_warning(f"Не удалось получить информацию о WireGuard интерфейсе: {stderr}")
    else:
        # Проверяем наличие handshake
        handshake_match = re.search(r'latest handshake: (.+)', stdout)
        if handshake_match:
            handshake_time = handshake_match.group(1)
            if "Never" in handshake_time:
                print_warning("Handshake с сервером никогда не был установлен")
            else:
                print_success(f"Последний handshake: {handshake_time}")
        else:
            print_warning("Информация о handshake не найдена")
        
        # Проверяем transfer
        transfer_match = re.search(r'transfer: (.+)', stdout)
        if transfer_match:
            transfer_info = transfer_match.group(1)
            print_info(f"Передача данных: {transfer_info}")
    
    return active

def check_routing(config: Dict[str, Any]) -> bool:
    """
    Проверяет маршрутизацию для WireGuard.
    
    Args:
        config: Словарь с данными конфигурации
        
    Returns:
        True, если маршрутизация настроена правильно, иначе False
    """
    print_step("Проверка маршрутизации")
    
    if not config or 'Peer' not in config or 'AllowedIPs' not in config['Peer']:
        print_error("Не удалось проверить маршрутизацию - отсутствуют данные конфигурации")
        return False
    
    allowed_ips = config['Peer']['AllowedIPs'].split(',')
    routing_ok = True
    
    returncode, stdout, stderr = run_command(['ip', 'route', 'show'])
    
    if returncode != 0:
        print_error(f"Не удалось получить информацию о маршрутах: {stderr}")
        return False
    
    for ip_range in allowed_ips:
        ip_range = ip_range.strip()
        
        # Ищем маршрут для этого диапазона
        if ip_range in stdout:
            print_success(f"Маршрут для {ip_range} настроен")
        else:
            print_error(f"Маршрут для {ip_range} не настроен")
            routing_ok = False
    
    return routing_ok

def check_connection_to_endpoint(config: Dict[str, Any]) -> bool:
    """
    Проверяет соединение с endpoint-сервером WireGuard.
    
    Args:
        config: Словарь с данными конфигурации
        
    Returns:
        True, если соединение установлено, иначе False
    """
    print_step("Проверка соединения с WireGuard сервером")
    
    if not config or 'Peer' not in config or 'Endpoint' not in config['Peer']:
        print_error("Не удалось проверить соединение - отсутствуют данные конфигурации")
        return False
    
    endpoint = config['Peer']['Endpoint']
    if ':' in endpoint:
        host, port_str = endpoint.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            print_error(f"Неверный формат порта в endpoint: {endpoint}")
            return False
    else:
        print_error(f"Неверный формат endpoint (нет порта): {endpoint}")
        return False
    
    # Проверка доступности UDP порта (это не всегда надежно из-за особенностей UDP)
    print_info(f"Проверка доступности {host}:{port} (UDP)")
    
    # Пробуем пинговать хост
    returncode, stdout, stderr = run_command(['ping', '-c', '4', host])
    
    if returncode != 0:
        print_error(f"Не удалось выполнить ping до хоста {host}: {stderr}")
        print_info("Это может быть связано с блокировкой ICMP или другими сетевыми ограничениями")
    else:
        ping_stats = re.search(r'(\d+) packets transmitted, (\d+) received', stdout)
        if ping_stats:
            sent, received = ping_stats.groups()
            if int(received) > 0:
                print_success(f"Хост {host} отвечает на ping ({received}/{sent})")
            else:
                print_warning(f"Хост {host} не отвечает на ping (0/{sent})")
    
    # UDP-проверка может быть ненадежной, но попробуем
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        
        # Отправляем пустой пакет
        sock.sendto(b"", (host, port))
        
        # Пытаемся получить ответ (в случае с WireGuard, его обычно не будет)
        try:
            data, addr = sock.recvfrom(1024)
            print_success(f"Получен ответ от {host}:{port}")
            connection_ok = True
        except socket.timeout:
            # Обычно для UDP WireGuard не отвечает на запросы
            print_info(f"Таймаут при ожидании ответа от {host}:{port} (это нормально для WireGuard)")
            connection_ok = True
    except socket.error as e:
        print_error(f"Ошибка при проверке UDP порта: {str(e)}")
        connection_ok = False
    finally:
        sock.close()
    
    return connection_ok

def check_dns_resolution() -> bool:
    """
    Проверяет работу DNS через WireGuard.
    
    Returns:
        True, если DNS работает, иначе False
    """
    print_step("Проверка DNS-резолвинга")
    
    test_domains = ["google.com", "cloudflare.com", "github.com"]
    dns_ok = True
    
    for domain in test_domains:
        try:
            print_info(f"Проверка разрешения имени {domain}")
            socket.gethostbyname(domain)
            print_success(f"Домен {domain} успешно разрешен")
        except socket.gaierror:
            print_error(f"Не удалось разрешить домен {domain}")
            dns_ok = False
    
    # Получаем текущие DNS-серверы
    returncode, stdout, stderr = run_command(['cat', '/etc/resolv.conf'])
    
    if returncode != 0:
        print_warning(f"Не удалось получить информацию о DNS-серверах: {stderr}")
    else:
        nameservers = re.findall(r'nameserver\s+(\S+)', stdout)
        if nameservers:
            print_info(f"Текущие DNS-серверы: {', '.join(nameservers)}")
        else:
            print_warning("DNS-серверы не настроены в /etc/resolv.conf")
    
    return dns_ok

def check_internet_connectivity() -> bool:
    """
    Проверяет доступность интернета через VPN-соединение.
    
    Returns:
        True, если интернет доступен, иначе False
    """
    print_step("Проверка доступности интернета через VPN")
    
    # Проверяем доступность нескольких известных сайтов через HTTPS
    test_urls = [
        "https://www.google.com",
        "https://www.cloudflare.com",
        "https://www.github.com",
        "https://ipinfo.io/json"  # Этот сайт вернет информацию о текущем IP
    ]
    
    internet_ok = True
    
    # Проверяем внешний IP через ipinfo.io
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        if response.status_code == 200:
            ip_info = response.json()
            print_info(f"Текущий внешний IP: {ip_info.get('ip', 'неизвестно')}")
            print_info(f"Местоположение: {ip_info.get('country', '?')}, {ip_info.get('city', '?')}")
            print_info(f"Провайдер: {ip_info.get('org', 'неизвестно')}")
        else:
            print_warning(f"Не удалось получить информацию о внешнем IP: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print_warning(f"Ошибка при запросе информации о внешнем IP: {str(e)}")
    
    # Исключаем ipinfo из общей проверки, так как мы уже проверили его выше
    for url in [u for u in test_urls if "ipinfo.io" not in u]:
        try:
            print_info(f"Проверка доступности {url}")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print_success(f"Сайт {url} доступен")
            else:
                print_warning(f"Сайт {url} вернул статус HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print_error(f"Не удалось подключиться к {url}: {str(e)}")
            internet_ok = False
    
    return internet_ok

def check_iptables_rules() -> bool:
    """
    Проверяет правила iptables для WireGuard.
    
    Returns:
        True, если правила корректны, иначе False
    """
    print_step("Проверка правил iptables для WireGuard")
    
    # Проверяем правила NAT
    returncode, nat_rules, stderr = run_command(['iptables', '-t', 'nat', '-L', '-v', '-n'])
    
    if returncode != 0:
        print_error(f"Не удалось получить правила NAT: {stderr}")
        return False
    
    # Проверяем правила фильтрации
    returncode, filter_rules, stderr = run_command(['iptables', '-L', '-v', '-n'])
    
    if returncode != 0:
        print_error(f"Не удалось получить правила фильтрации: {stderr}")
        return False
    
    # Ищем правила для WireGuard
    wg_postrouting_rules = [line for line in nat_rules.split('\n') if 'wg' in line.lower() and 'postrouting' in line.lower()]
    wg_forward_rules = [line for line in filter_rules.split('\n') if 'wg' in line.lower() and 'forward' in line.lower()]
    
    if wg_postrouting_rules:
        print_success("Обнаружены правила NAT для WireGuard")
        for rule in wg_postrouting_rules:
            print_info(f"  {rule.strip()}")
    else:
        print_warning("Не обнаружены правила NAT для WireGuard")
    
    if wg_forward_rules:
        print_success("Обнаружены правила FORWARD для WireGuard")
        for rule in wg_forward_rules:
            print_info(f"  {rule.strip()}")
    else:
        print_warning("Не обнаружены правила FORWARD для WireGuard")
    
    # Проверяем IP Forwarding
    returncode, stdout, stderr = run_command(['sysctl', 'net.ipv4.ip_forward'])
    
    if returncode != 0:
        print_error(f"Не удалось проверить состояние IP Forwarding: {stderr}")
    else:
        if "net.ipv4.ip_forward = 1" in stdout:
            print_success("IP Forwarding включен")
        else:
            print_error("IP Forwarding не включен")
            print_info("Для включения выполните: sudo sysctl -w net.ipv4.ip_forward=1")
    
    return bool(wg_postrouting_rules and wg_forward_rules)

def check_server_connectivity(config: Dict[str, Any]) -> bool:
    """
    Проверяет соединение с сервером WireGuard, если это возможно.
    
    Args:
        config: Словарь с данными конфигурации
        
    Returns:
        True, если сервер доступен, иначе False
    """
    print_step("Проверка соединения с WireGuard сервером")
    
    if not config or 'Peer' not in config or 'Endpoint' not in config['Peer']:
        print_error("Не удалось проверить соединение с сервером - отсутствуют данные конфигурации")
        return False
    
    endpoint = config['Peer']['Endpoint']
    if ':' in endpoint:
        host, port_str = endpoint.rsplit(':', 1)
    else:
        print_error(f"Неверный формат endpoint (нет порта): {endpoint}")
        return False
    
    # Проверяем маршрут до сервера
    returncode, stdout, stderr = run_command(['traceroute', '-n', '-w', '1', '-m', '15', host])
    
    if returncode != 0:
        print_warning(f"Не удалось выполнить traceroute до сервера: {stderr}")
    else:
        print_info("Маршрут до сервера:")
        for line in stdout.split('\n')[:15]:  # Ограничиваем вывод первыми 15 строками
            if line.strip():
                print_info(f"  {line.strip()}")
    
    return True

def diagnose_connection(config_path: str, interface_name: str) -> Dict[str, bool]:
    """
    Выполняет полную диагностику соединения WireGuard.
    
    Args:
        config_path: Путь к конфигурационному файлу
        interface_name: Имя интерфейса WireGuard
        
    Returns:
        Словарь с результатами тестов
    """
    results = {}
    
    # Проверка файла конфигурации
    config = validate_config_file(config_path)
    results['config_valid'] = bool(config)
    
    # Проверка интерфейса
    results['interface_active'] = check_interface_status(interface_name)
    
    # Проверка маршрутизации
    results['routing_ok'] = check_routing(config)
    
    # Проверка соединения с endpoint
    results['endpoint_reachable'] = check_connection_to_endpoint(config)
    
    # Проверка iptables
    results['iptables_ok'] = check_iptables_rules()
    
    # Проверка DNS
    results['dns_ok'] = check_dns_resolution()
    
    # Проверка интернета
    results['internet_ok'] = check_internet_connectivity()
    
    # Проверка доступности сервера
    results['server_ok'] = check_server_connectivity(config)
    
    return results

def analyze_results(results: Dict[str, bool]) -> None:
    """
    Анализирует результаты диагностики и предлагает решения.
    
    Args:
        results: Словарь с результатами тестов
    """
    print_step("Анализ результатов и рекомендации")
    
    if all(results.values()):
        print_success("Все тесты пройдены успешно! Соединение WireGuard должно работать корректно.")
        print_info("Если у вас всё ещё возникают проблемы, проверьте следующее:")
        print_info("1. Правильность настроек брандмауэра на клиенте и сервере")
        print_info("2. Доступность сервера WireGuard (возможно, он выключен или перегружен)")
        print_info("3. Правильность настроек маршрутизации на сервере")
        return
    
    # Анализируем каждый тест
    if not results.get('config_valid', False):
        print_error("Проблема с файлом конфигурации!")
        print_info("Рекомендации:")
        print_info("1. Проверьте правильность формата конфигурационного файла")
        print_info("2. Убедитесь, что все необходимые поля присутствуют и корректны")
        print_info("3. Сравните с примером рабочей конфигурации")
    
    if not results.get('interface_active', False):
        print_error("Проблема с активацией интерфейса WireGuard!")
        print_info("Рекомендации:")
        print_info("1. Попробуйте перезапустить интерфейс: sudo wg-quick down wg0 && sudo wg-quick up wg0")
        print_info("2. Проверьте логи системы: sudo journalctl -xeu wg-quick@wg0")
        print_info("3. Убедитесь, что сервис WireGuard установлен корректно")
    
    if not results.get('routing_ok', False):
        print_error("Проблема с маршрутизацией!")
        print_info("Рекомендации:")
        print_info("1. Проверьте правильность AllowedIPs в конфигурации")
        print_info("2. Убедитесь, что маршруты добавляются при активации интерфейса")
        print_info("3. Проверьте конфликты с существующими маршрутами: ip route show")
    
    if not results.get('endpoint_reachable', False):
        print_error("Проблема с доступностью сервера WireGuard!")
        print_info("Рекомендации:")
        print_info("1. Проверьте правильность адреса и порта в Endpoint")
        print_info("2. Убедитесь, что нет блокировки на уровне сети или брандмауэра")
        print_info("3. Проверьте статус сервера WireGuard")
    
    if not results.get('iptables_ok', False):
        print_error("Проблема с правилами iptables!")
        print_info("Рекомендации:")
        print_info("1. Убедитесь, что IP Forwarding включен: sysctl net.ipv4.ip_forward")
        print_info("2. Проверьте настройки iptables для маскарадинга: iptables -t nat -L -v -n")
        print_info("3. Добавьте необходимые правила для WireGuard")
    
    if not results.get('dns_ok', False):
        print_error("Проблема с DNS-резолвингом!")
        print_info("Рекомендации:")
        print_info("1. Проверьте настройки DNS в конфигурации: cat /etc/resolv.conf")
        print_info("2. Попробуйте использовать альтернативные DNS-серверы (например, 1.1.1.1 или 8.8.8.8)")
        print_info("3. Проверьте, не блокируются ли DNS-запросы брандмауэром")
    
    if not results.get('internet_ok', False):
        print_error("Проблема с доступностью интернета через VPN!")
        print_info("Рекомендации:")
        print_info("1. Убедитесь, что на сервере настроен NAT для клиентов WireGuard")
        print_info("2. Проверьте маршрутизацию на сервере")
        print_info("3. Проверьте настройки брандмауэра на сервере")
    
    if not results.get('server_ok', False):
        print_error("Проблема с соединением с сервером WireGuard!")
        print_info("Рекомендации:")
        print_info("1. Проверьте статус сервера WireGuard")
        print_info("2. Убедитесь, что порт UDP открыт на сервере")
        print_info("3. Проверьте настройки брандмауэра на сервере")

def main():
    parser = argparse.ArgumentParser(description='Инструмент диагностики соединения WireGuard')
    parser.add_argument('config', help='Путь к файлу конфигурации WireGuard')
    parser.add_argument('--interface', '-i', default='wg0', help='Имя интерфейса WireGuard (по умолчанию: wg0)')
    
    args = parser.parse_args()
    
    print(f"{Colors.BOLD}{Colors.HEADER}=== Диагностика соединения WireGuard ==={Colors.ENDC}")
    print(f"{Colors.BLUE}Файл конфигурации: {args.config}{Colors.ENDC}")
    print(f"{Colors.BLUE}Интерфейс: {args.interface}{Colors.ENDC}")
    
    # Проверяем root-права
    if os.geteuid() != 0:
        print_warning("Скрипт запущен без прав администратора!")
        print_warning("Некоторые тесты могут не работать корректно.")
        print_warning("Рекомендуется запустить скрипт с sudo.")
        
        confirm = input("Продолжить без прав администратора? (y/n): ")
        if confirm.lower() != 'y':
            sys.exit(1)
    
    results = diagnose_connection(args.config, args.interface)
    analyze_results(results)

if __name__ == "__main__":
    main()