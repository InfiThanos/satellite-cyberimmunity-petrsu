from multiprocessing import Queue
from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import CRITICALITY_STR, LOG_DEBUG, \
    LOG_ERROR, LOG_INFO, DEFAULT_LOG_LEVEL, \
    OPTICS_CONTROL_QUEUE_NAME, ZONE_CHECK_QUEUE_NAME, CAMERA_QUEUE_NAME, \
    SECURITY_MONITOR_QUEUE_NAME, CENTRAL_CONTROL_SYSTEM_QUEUE_NAME, ORBIT_DRAWER_QUEUE_NAME


class OpticsCheck(BaseCustomProcess):
    """ Модуль управления потической аппаратурой """
    log_prefix = "[OPTIC_CHECK]"
    event_source_name = ZONE_CHECK_QUEUE_NAME
    events_q_name = event_source_name
    m_lat, m_lon = 0.0


    def __init__(
            self,
            queues_dir: QueuesDirectory,
            log_level: int = DEFAULT_LOG_LEVEL
    ):
        super().__init__(
            log_prefix=OpticsCheck.log_prefix,
            queues_dir=queues_dir,
            events_q_name=OpticsCheck.event_source_name,
            event_source_name=OpticsCheck.event_source_name,
            log_level=log_level)

        self._log_message(LOG_INFO, f"модуль проверки зоны съемки создан")


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
                    case 'request_photo':
                        self._send_photo_request()
                    case 'check_photo':
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        self.m_lat, self.m_lon = event.parameters
                        q.put(
                            Event(
                                source=self._event_source_name,
                                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                                operation='request_zone',
                                parameters=None))
                        self._log_message(LOG_DEBUG, f"проверяем законность снимка ({self.m_lat}, {self.m_lon})")
                    case 'post_photo':
                        rectangles = event.parameters
                        for rect in rectangles:
                            lon1, lat1, lon2, lat2 = rect
                            # Проверяем, что координаты полностью внутри текущего прямоугольника
                            if ((lat1 <= self.m_lat <= lat2) and (lon1 <= self.m_lon <= lon2)):
                                return
                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name,
                                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                                operation='add_photo',
                                parameters=(self.m_lat, self.m_lon)))
                        q.put(
                            Event(
                                source=self._event_source_name,
                                destination=ORBIT_DRAWER_QUEUE_NAME,
                                operation='update_photo',
                                parameters=(self.m_lat, self.m_lon)))
                        self._log_message(LOG_DEBUG, f"сохраняем снимок ({self.m_lat}, {self.m_lon})")

            except Empty:
                break


    def run(self):
        self._log_message(LOG_INFO, f"модуль проверки зоны съемки активен")

        while self._quit is False:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка системы проверки зоны съемки: {e}")


    def _send_photo_request(self):
        # Запрос на снимок
        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        q.put(
            Event(
                source=self._event_source_name,
                destination=CAMERA_QUEUE_NAME,
                operation='request_photo',
                parameters=None))
        self._log_message(LOG_DEBUG, f"запрашиваем снимок")