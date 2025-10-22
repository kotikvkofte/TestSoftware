import os
import time

import requests
import pytest

@pytest.mark.timeout(20)
def test_redfish_auth_session_created():
    host = "127.0.0.1"
    port = "2443"
    username = "root"
    password = "0penBmc"

    url = f"https://{host}:{port}/redfish/v1/SessionService/Sessions"
    payload = {"UserName": username, "Password": password}

    resp = requests.post(url, json=payload, verify=False, timeout=15)

    assert resp.status_code == 201, f"Ожидался 201, получено {resp.status_code}: {resp.text[:201]}"

    token = resp.headers.get("X-Auth-Token")
    assert token, f"Токен сессии X-Auth-Token отсутствует в заголовках ответа. Headers: {dict(resp.headers)}"

@pytest.mark.timeout(20)
def test_get_system_info():
    host = "127.0.0.1"
    port = "2443"
    username = "root"
    password = "0penBmc"

    session_url = f"https://{host}:{port}/redfish/v1/SessionService/Sessions"
    auth_resp = requests.post(session_url,
                              json={"UserName": username, "Password": password},
                              verify=False, timeout=15)
    assert auth_resp.status_code in (200, 201), (
        f"Не удалось аутентифицироваться: {auth_resp.status_code} {auth_resp.text[:200]}"
    )
    token = auth_resp.headers.get("X-Auth-Token")
    assert token, "В ответе на аутентификацию нет заголовка X-Auth-Token"

    # GET /Systems/system
    systems_url = f"https://{host}:{port}/redfish/v1/Systems/system"
    r = requests.get(systems_url, headers={"X-Auth-Token": token}, verify=False, timeout=15)

    assert r.status_code == 200, f"Ожидался 200, получено {r.status_code}: {r.text[:200]}"

    # наличие полей в JSON
    data = r.json()
    assert "Status" in data, "В ответе отсутствует поле 'Status'"
    assert "PowerState" in data, "В ответе отсутствует поле 'PowerState'"

@pytest.mark.timeout(120)
def test_power_control_turn_on():
    host = "127.0.0.1"
    port = "2443"
    username = "root"
    password = "0penBmc"

    base = f"https://{host}:{port}/redfish/v1"

    session_url = f"{base}/SessionService/Sessions"
    auth_resp = requests.post(
        session_url,
        json={"UserName": username, "Password": password},
        verify=False,
        timeout=15,
    )
    assert auth_resp.status_code in (200, 201), (
        f"Не удалось аутентифицироваться: {auth_resp.status_code} {auth_resp.text[:200]}"
    )
    token = auth_resp.headers.get("X-Auth-Token")
    assert token, "Нет X-Auth-Token в заголовках ответа"
    headers = {"X-Auth-Token": token}

    # Отправляем Reset с ResetType="On"
    reset_url = f"{base}/Systems/system/Actions/ComputerSystem.Reset"
    reset_resp = requests.post(
        reset_url,
        json={"ResetType": "On"},
        headers=headers,
        verify=False,
        timeout=15,
    )

    assert reset_resp.status_code == 204, (
        f"Ожидался 202 Accepted, получено {reset_resp.status_code}: {reset_resp.text[:200]}"
    )

    systems_url = f"{base}/Systems/system"
    deadline = time.time() + 20
    last_state = None
    while time.time() < deadline:
        r = requests.get(systems_url, headers=headers, verify=False, timeout=15)
        if r.status_code == 200:
            last_state = r.json().get("PowerState")
            if last_state == "On":
                break
        time.sleep(2)

    assert last_state == "Off", f"PowerState='{last_state}', ожидалось 'Off'"

@pytest.mark.timeout(20)
def test_thermalmetrics_temperature_is_empty():
    host, port = "127.0.0.1", "2443"
    user, pwd = "root", "0penBmc"
    base = f"https://{host}:{port}/redfish/v1"

    auth = requests.post(f"{base}/SessionService/Sessions",
                         json={"UserName": user, "Password": pwd},
                         verify=False, timeout=15)
    assert auth.status_code in (200, 201), f"Auth failed: {auth.status_code} {auth.text[:200]}"
    token = auth.headers.get("X-Auth-Token")
    assert token, "Нет X-Auth-Token в заголовках ответа"
    hdr = {"X-Auth-Token": token}

    # Читаем ThermalMetrics
    r = requests.get(f"{base}/Chassis/chassis/ThermalSubsystem/ThermalMetrics",
                     headers=hdr, verify=False, timeout=15)
    assert r.status_code == 200, f"Ожидался 200, получено {r.status_code}: {r.text[:200]}"

    body = r.json() or {}
    assert "TemperatureReadingsCelsius" in body, "В ответе нет поля TemperatureReadingsCelsius"

    readings = body.get("TemperatureReadingsCelsius")
    assert isinstance(readings, list), "TemperatureReadingsCelsius должен быть списком"
    assert len(readings) == 0, f"Ожидался пустой список TemperatureReadingsCelsius, получили: {readings}" 