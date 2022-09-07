from locust import HttpUser, task


class HelloWorldUser(HttpUser):
    @task
    def hello_mit(self):
        self.client.get("https://www.mit.edu")
