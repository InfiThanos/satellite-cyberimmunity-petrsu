from multiprocessing import Queue
from queue import Empty

import math

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event, ControlEvent
from src.system.config import CRITICALITY_STR, LOG_DEBUG, \
    LOG_ERROR, LOG_INFO, DEFAULT_LOG_LEVEL, \
    ORBIT_CONTROL_QUEUE_NAME, ORBIT_CHECK_QUEUE_NAME, SATELITE_QUEUE_NAME, SECURITY_MONITOR_QUEUE_NAME


class OrbitCheck(BaseCustomProcess):
    """ Модуль проверки корректности орбиты """
    log_prefix = "[ORBIT_CHECK]"
    event_source_name = ORBIT_CHECK_QUEUE_NAME
    events_q_name = event_source_name


    def __init__(
            self,
            queues_dir: QueuesDirectory,
            log_level: int = DEFAULT_LOG_LEVEL
    ):
        super().__init__(
            log_prefix=OrbitCheck.log_prefix,
            queues_dir=queues_dir,
            events_q_name=OrbitCheck.event_source_name,
            event_source_name=OrbitCheck.event_source_name,
            log_level=log_level)

        self._log_message(LOG_INFO, "модуль проверки корректности орбиты создан")


    def _check_control_q(self):
        try:
            request: ControlEvent = self._control_q.get_nowait()
            self._log_message(
                LOG_DEBUG, f"проверяем запрос {request}")
            if not isinstance(request, ControlEvent):
                return
            if request.operation == 'stop':
                self._quit = True
        except Empty:
            # никаких команд не поступило, ну и ладно
            pass


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
                    case 'check_orbit':
                        # Извлекаем параметры новой орбиты
                        altitude, raan, inclination = event.parameters
                        self._log_message("Система проверки корректности орбиты получила новые параметры")
                        self._check_orbit(altitude, raan, inclination)
            except Empty:
                break

    def run(self):
        self._log_message(LOG_INFO, f"модуль проверки корректности орбиты активен")

        while self._quit is False:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка модуля проверки корректности орбиты: {e}")


    def _check_orbit(self, altitude, raan, inclination):
        """
            Проверяет корректность параметров орбиты:
            - altitude: высота в метрах (≥ 160 км, ≤ 35 786 км)
            - raan: долгота восходящего узла в радианах (от -70° до +70°)
            - inclination: наклонение в радианах (от -70° до +70°)
        """

        # Проверка высоты (altitude)
        MIN_ALTITUDE = 160_000  # 160 км (ниже — слишком низко для спутника)
        MAX_ALTITUDE = 35_786_000  # 35 786 км (геостационарная орбита)

        if not (MIN_ALTITUDE <= altitude <= MAX_ALTITUDE):
            self._log_message(LOG_ERROR,
                f"Ошибка: высота {altitude / 1000:.1f} км вне диапазона "
                f"[{MIN_ALTITUDE / 1000:.0f} км, {MAX_ALTITUDE / 1000:.0f} км]")
            return

        # Проверка RAAN (raan)
        MIN_ANGLE_RAD = math.radians(-70)  # -70° в радианах
        MAX_ANGLE_RAD = math.radians(70)  # +70° в радианах

        if not (MIN_ANGLE_RAD <= raan <= MAX_ANGLE_RAD):
            self._log_message(LOG_ERROR,
                f"Ошибка: RAAN {math.degrees(raan):.1f}° вне диапазона "
                f"[{math.degrees(MIN_ANGLE_RAD):.0f}°, {math.degrees(MAX_ANGLE_RAD):.0f}°]"
            )
            return

        #Проверка наклонения (inclination)
        if not (MIN_ANGLE_RAD <= inclination <= MAX_ANGLE_RAD):
            self._log_message(LOG_ERROR,
                f"Ошибка: наклонение {math.degrees(inclination):.1f}° вне диапазона "
                f"[{math.degrees(MIN_ANGLE_RAD):.0f}°, {math.degrees(MAX_ANGLE_RAD):.0f}°]"
            )
            return

        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        q.put(
            Event(
                source=self._event_source_name,
                destination=SATELITE_QUEUE_NAME,
                operation='change_orbit',
                parameters=(altitude, inclination, raan)))