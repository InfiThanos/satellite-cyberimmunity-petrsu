from multiprocessing import Queue
from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import CLIENT_QUEUE_NAME
from src.system.config import SATELLITE_CONTROL_SYSTEM_QUEUE_NAME, SECURITY_MONITOR_QUEUE_NAME
from src.system.config import COMMAND_HANDLER_QUEUE_NAME
from src.system.config import DEFAULT_LOG_LEVEL, LOG_ERROR, LOG_INFO

from hashlib import sha512

class Client(BaseCustomProcess):
    """ Модуль клиента """
    log_prefix = "[CLIENT]"
    event_source_name = CLIENT_QUEUE_NAME
    events_q_name = event_source_name

    def __init__(self, queues_dir: QueuesDirectory, log_level: int = DEFAULT_LOG_LEVEL):
        # вызываем конструктор базового класса
        super().__init__(log_prefix=Client.log_prefix, queues_dir=queues_dir,
                         events_q_name=Client.event_source_name,
                         event_source_name=Client.event_source_name,
                         log_level=log_level)
        
        self._log_message(LOG_INFO, f"модуль клиента создан")

        
    def _check_events_q(self):
        """ Метод проверяет наличие сообщений для данного компонента системы """
        while True:
            try:
                # Получаем сообщение из очереди
                event: Event = self._events_q.get_nowait()

                # Проверяем, что сообщение принадлежит типу Event (см. файл event_types.py)
                if not isinstance(event, Event):
                    return

                # Проверяем вид операции и обрабатываем
                match event.operation:
                    case 'send_code':
                        login, password, filename = event.parameters
                        self._log_message(LOG_INFO, f"{login} {password} {filename}\n")


            except Empty:
               break


    def run(self):
        self._log_message(LOG_INFO, f"модуль регистрации активен")

        while self._quit is False:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка системы регистрации: {e}")


