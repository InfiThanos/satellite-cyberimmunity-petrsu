from multiprocessing import Queue
from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import DATA_STORAGE_QUEUE_NAME, OPTICS_CONTROL_QUEUE_NAME, \
     ORBIT_CONTROL_QUEUE_NAME, ZONE_CHECK_QUEUE_NAME
from src.system.config import ORBIT_CONTROL_QUEUE_NAME, DEFAULT_LOG_LEVEL, LOG_ERROR, LOG_INFO

import re

class CentralControlSystem(BaseCustomProcess):
    """ Модуль ЦСУ """
    log_prefix = "[CSU]"
    event_source_name = CENTRAL_CONTROL_SYSTEM_QUEUE_NAME
    events_q_name = event_source_name

    def __init__(self, queues_dir: QueuesDirectory, log_level: int = DEFAULT_LOG_LEVEL):
        # вызываем конструктор базового класса
        super().__init__(log_prefix=MyInterpreter.log_prefix, queues_dir=queues_dir,
                         events_q_name=MyInterpreter.event_source_name,
                         event_source_name=MyInterpreter.event_source_name,
                         log_level=log_level)
        
        self._log_message(LOG_INFO, f"модуль ЦСУ создан")


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
                    case 'ORBIT':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name, 
                                destination=ORBIT_CONTROL_QUEUE_NAME, 
                                operation='update_photo_map', 
                                parameters=event.parameters
                        self._log_message(LOG_DEBUG, f"рисуем снимок ({lat}, {lon})")
                        break
                    case 'ADD ZONE':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name, 
                                destination=DATA_STORAGE_QUEUE_NAME, 
                                operation='add_zone', 
                                parameters=event.parameters
                        self._log_message(LOG_DEBUG, f"рисуем снимок ({lat}, {lon})")
                        break
                    case 'REMOVE ZONE':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name, 
                                destination=DATA_STORAGE_QUEUE_NAME, 
                                operation='remove', 
                                parameters=event.parameters
                        self._log_message(LOG_DEBUG, f"рисуем снимок ({lat}, {lon})")
                        break
                    case 'MAKE PHOTO':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name, 
                                destination=OPTICS_CONTROL_QUEUE_NAME, 
                                operation='request_photo', 
                                parameters=event.parameters
                        self._log_message(LOG_DEBUG, f"рисуем снимок ({lat}, {lon})")
                        break
                    case 'request_zone':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name, 
                                destination=DATA_STORAGE_QUEUE_NAME, 
                                operation='request_zone', 
                                parameters=event.parameters
                        self._log_message(LOG_DEBUG, f"рисуем снимок ({lat}, {lon})")
                        break
                    case 'update_photo':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name, 
                                destination=ZONE_CHECK_QUEUE_NAME, 
                                operation='post_photo', 
                                parameters=event.parameters
                        self._log_message(LOG_DEBUG, f"рисуем снимок ({lat}, {lon})")
                        break
                               
            except Empty:
                break


    def run(self):
        self._log_message(LOG_INFO, f"модуль ЦСУ активен")

        while self._quit is False:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка ЦСУ: {e}")
