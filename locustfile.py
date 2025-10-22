from locust import HttpUser, task, between, tag

BMC_HOST = "127.0.0.1"
BMC_USER = "root"
BMC_PASS = "0penBmc"
BMC_SCHEME = "https"
BMC_PORT = "2443"
SYSTEM_PATH = "/redfish/v1/Systems/system"

OPENBMC_BASE = f"{BMC_SCHEME}://{BMC_HOST}:{BMC_PORT}"


class OpenBmcUser(HttpUser):
    host = OPENBMC_BASE
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.auth = (BMC_USER, BMC_PASS)

    @tag("openbmc", "system")
    @task(2)
    def system_info(self):
        r = self.client.get(
            SYSTEM_PATH,
            auth=self.auth,
            verify=False,
            name="/redfish/v1/Systems/system",
        )
        assert r.status_code == 200
        data = r.json()
        assert "Id" in data and "Name" in data

    @tag("openbmc", "power")
    @task(1)
    def power_state(self):
        r = self.client.get(
            SYSTEM_PATH,
            auth=self.auth,
            verify=False,
            name="/redfish/v1/Systems/system (PowerState)",
        )
        assert r.status_code == 200
        data = r.json()
        assert "PowerState" in data


class PublicApiUser(HttpUser):
    host = "https://jsonplaceholder.typicode.com"
    wait_time = between(0.5, 1.5)

    @tag("public", "posts")
    @task(2)
    def list_posts(self):
        r = self.client.get("/posts", name="JSONPlaceholder /posts")
        assert r.status_code == 200
        assert isinstance(r.json(), list) and len(r.json()) > 0

    @tag("public", "weather")
    @task(1)
    def novosibirsk_weather(self):
        r = self.client.get("https://wttr.in/Novosibirsk?format=j1",
                            name="wttr.in Novosibirsk?format=j1")
        assert r.status_code == 200
        assert "current_condition" in r.json()
