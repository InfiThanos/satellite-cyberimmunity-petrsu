from multiprocessing import Queue
from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import CLIENT_QUEUE_NAME
from src.system.config import SATELLITE_CONTROL_SYSTEM_QUEUE_NAME, SECURITY_MONITOR_QUEUE_NAME
from src.system.config import COMMAND_HANDLER_QUEUE_NAME
from src.system.config import DEFAULT_LOG_LEVEL, LOG_ERROR, LOG_INFO

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
        self.current_task = "name file is set"
        self.name_file = ''
        self.login = ''
        self.password = ''
        
    def _check_events_q(self):
        """ Метод проверяет наличие сообщений для данного компонента системы """
        while True:
            try:
                if self.current_task == 'password is set':
                    q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                    q.put(
                    Event(source=self._event_source_name,
                          destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                          operation='print',
                          parameters='Введите 1, чтобы загрузить файл, введите 2, чтобы завершить систему'))
                    q.put(
                    Event(source=self._event_source_name,
                          destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                          operation='input',
                          parameters=None))
                    self.current_task = 'get an action'
                    break
                elif self.current_task == 'get an action':
                    # Получаем сообщение из очереди
                    event: Event = self._events_q.get_nowait()

                    # Проверяем, что сообщение принадлежит типу Event (см. Файл event_types.py)
                    if not isinstance(event, Event):
                        return

                    if event.operation == 'get input':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        if event.parameters == '1':
                            q.put(
                            Event(source=self._event_source_name,
                                  destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                                  operation='print',
                                  parameters='Введите имя файла'))
                            q.put(
                            Event(source=self._event_source_name,
                                  destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                                  operation='input',
                                  parameters=None))
                            self.current_task = 'get name file'
                            break
                        elif event.parameters == '2':
                            q.put(
                            Event(source=self._event_source_name,
                                  destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                                  operation='end',
                                  parameters=None))
                            break
                        else:
                            self.current_task = 'password is set'
                            break
                elif self.current_task == 'get name file':
                    # Получаем сообщение из очереди
                    event: Event = self._events_q.get_nowait()

                    # Проверяем, что сообщение принадлежит типу Event (см. файл event_types.py)
                    if not isinstance(event, Event):
                        return

                    if event.operation == 'get input':
                        self.name_file = event.parameters
                        self.current_task = 'name file is set'
                        break
                elif self.current_task == 'name file is set':
                    q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                    q.put(
                    Event(source=self._event_source_name,
                          destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                          operation='print',
                          parameters='Введите логин'))
                    q.put(
                    Event(source=self._event_source_name,
                          destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                          operation='input',
                          parameters=None))
                    self.current_task = 'get login'
                    break
                elif self.current_task == 'get login':
                    # Получаем сообщение из очереди
                    event: Event = self._events_q.get_nowait()

                    # Проверяем, что сообщение принадлежит типу Event (см. файл event_types.py)
                    if not isinstance(event, Event):
                        return

                    if event.operation == 'get input':
                        self.login = event.parameters
                        self.current_task = 'login is set'
                        break
                elif self.current_task == 'login is set':
                    q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                    q.put(
                    Event(source=self._event_source_name,
                          destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                          operation='print',
                          parameters='Введите пароль'))
                    q.put(
                    Event(source=self._event_source_name,
                          destination=SATELLITE_CONTROL_SYSTEM_QUEUE_NAME,
                          operation='input',
                          parameters=None))
                    self.current_task = 'get password'
                    break
                elif self.current_task == 'get password':
                    # Получаем сообщение из очереди
                    event: Event = self._events_q.get_nowait()

                    # Проверяем, что сообщение принадлежит типу Event (см. файл event_types.py)
                    if not isinstance(event, Event):
                        return

                    if event.operation == 'get input':
                        self.password = event.parameters
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                        Event(source=self._event_source_name,
                              destination=COMMAND_HANDLER_QUEUE_NAME,
                              operation='upload_file',
                              parameters=(self.name_file, self.login, self.password)))
                        self.current_task = 'password is set'
                        break
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


