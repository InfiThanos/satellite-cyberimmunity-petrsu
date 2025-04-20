from multiprocessing import Queue
from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import CRITICALITY_STR, LOG_DEBUG, \
    LOG_ERROR, LOG_INFO, DEFAULT_LOG_LEVEL, \
    SECURITY_MONITOR_QUEUE_NAME, CENTRAL_CONTROL_SYSTEM_QUEUE_NAME, ORBIT_DRAWER_QUEUE_NAME, DATA_STORAGE_QUEUE_NAME


class DataBase(BaseCustomProcess):
    """ Модуль хранения данных """
    log_prefix = "[DATA_STORAGE]"
    event_source_name = DATA_STORAGE_QUEUE_NAME
    events_q_name = event_source_name
    photo_file = 'photo.txt'
    zone_file = 'zone.txt'


    def __init__(
            self,
            queues_dir: QueuesDirectory,
            log_level: int = DEFAULT_LOG_LEVEL
    ):
        super().__init__(
            log_prefix=DataBase.log_prefix,
            queues_dir=queues_dir,
            events_q_name=DataBase.event_source_name,
            event_source_name=DataBase.event_source_name,
            log_level=log_level)

        self._log_message(LOG_INFO, f"модуль хранения данных создан")


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
                    case 'add_zone':
                        id, lon1, lat1, lon2, lat2 = event.parameters

                        if ((lat1 >= lat2) or (lon1 >= lon2)):
                            self._log_message(LOG_ERROR, f"Некорректные координаты зоны, первая точка должна быть выше и левее второй")
                            return

                        id_exists = False
                        try:
                            with open(self.zone_file, 'r') as f:
                                for line in f:
                                    existing_id = line.split()[0]
                                    if existing_id == str(id):
                                        id_exists = True
                                        break
                        except FileNotFoundError:
                            pass

                        if not id_exists:
                            with open(self.zone_file, 'a') as f:
                                f.write(f"{id} {lon1} {lat1} {lon2} {lat2}\n")
                            self._log_message(LOG_DEBUG, f"добавляем новую зону ({id}, {lon1}, {lat1}, {lon2}, {lat2})")
                        else:
                            self._log_message(LOG_ERROR, f"зона с ID {id} уже существует! Запись не добавлена")

                    case 'delete_zone':
                        id = event.parameters
                        try:
                            with open(self.zone_file, 'r') as f:
                                lines = f.readlines()

                            new_lines = [line for line in lines if line.split()[0] != str(id)]

                            if len(new_lines) != len(lines):
                                with open(self.zone_file, 'w') as f:
                                    f.writelines(new_lines)
                                self._log_message(LOG_DEBUG, f"зона успешно удалена")
                            else:
                                self._log_message(LOG_ERROR, f"зона с ID {id} не найден! Запись не удалена")

                        except FileNotFoundError:
                            self._log_message(LOG_DEBUG, f"файл не найден")

                    case 'request_zone':
                        rectangles = []
                        try:
                            with open(self.zone_file, 'r') as file:
                                for line in file:
                                    parts = line.strip().split()
                                    if len(parts) == 5:  # Проверяем, что строка содержит 5 значений
                                        _, x1, y1, x2, y2 = parts  # Игнорируем первый элемент (ID)
                                        rectangles.append((float(x1), float(y1), float(x2), float(y2)))
                        except FileNotFoundError:
                            self._log_message(LOG_DEBUG, f"файл не найден")

                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                        q.put(
                            Event(
                                source=self._event_source_name,
                                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                                operation='update_photo',
                                parameters=rectangles))

                    case 'add_photo':
                        lat, lon = event.parameters
                        with open(self.photo_file, 'a') as f:
                            f.write(f"{lat} {lon}\n")
                        self._log_message(LOG_DEBUG, f"снимок сохранен в хранилище")

            except Empty:
                break


    def run(self):
        self._log_message(LOG_INFO, f"модуль хранения данных активен")

        while self._quit is False:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка системы хранения данных: {e}")

