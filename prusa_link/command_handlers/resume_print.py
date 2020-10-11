import logging

from prusa_link.command_handlers.try_until_state import TryUntilState
from prusa_link.default_settings import get_settings
from prusa_link.structures.model_classes import States

LOG = get_settings().LOG


log = logging.getLogger(__name__)
log.setLevel(LOG.COMMANDS)


class ResumePrint(TryUntilState):
    command_name = "resume print"

    def _run_command(self):
        self._try_until_state(gcode="M602", desired_state=States.PRINTING)

        # If we were file printing, the module itself will recognize
        # it should resume from serial
        # if self.file_printer.printing:
        #     self.file_printer.resume()
