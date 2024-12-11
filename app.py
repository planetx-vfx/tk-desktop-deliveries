# MIT License

# Copyright (c) 2022 Netherlands Film Academy

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import getpass
from pathlib import Path

from sgtk.platform import Application


class tkShotGridDeliveries(Application):
    """
    App to deliver Shots with the correct naming convention
    """

    def init_app(self):
        """Called as the application is being initialized"""
        self.engine.register_command("Deliveries", self.deliveries)

    def deliveries(self):
        """This function will open the application"""
        self.setup_sentry()

        app_payload = self.import_module("app")
        app_payload.controller.open_delivery_app(self)

    def setup_sentry(self):
        """
        Add Sentry error handling.
        """
        try:
            import sentry_sdk

            dsn = self.get_setting("sentry_dsn")
            if dsn is None or dsn == "":
                self.logger.error("Setting up Sentry failed. No DSN provided")
                return

            environment = "production"
            version = self.version
            if version == "Undefined":
                version = "0.0.0+dev"
                environment = "development"

            sentry_sdk.set_user({"id": getpass.getuser()})

            sentry_sdk.set_context(
                "app",
                {
                    "app_name": self.display_name,
                    "app_version": version,
                },
            )

            sentry_sdk.set_tags(
                {
                    "shotgrid.project.name": self.context.project["name"],
                    "shotgrid.project.id": self.context.project["id"],
                }
            )

            def before_send(event, hint) -> None:
                """Update event data before sending to Sentry."""
                paths = []
                for value in event["exception"]["values"]:
                    for frame in value["stacktrace"]["frames"]:
                        abs_path = Path(frame["abs_path"]).parent.as_posix()
                        paths.append(abs_path)

                base_path = Path(__file__).parent.as_posix()

                if not any(base_path in path for path in paths):
                    return None

                return event

            sentry_sdk.init(
                dsn=dsn,
                traces_sample_rate=1.0,
                enable_tracing=True,
                attach_stacktrace=True,
                include_source_context=True,
                before_send=before_send,
                release=version,
                environment=environment,
            )

            self.logger.info("Successfully setup Sentry.")
        except:
            self.logger.error("Setting up Sentry failed.")
