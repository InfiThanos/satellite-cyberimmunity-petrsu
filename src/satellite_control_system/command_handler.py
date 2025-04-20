from multiprocessing import Queue
from queue import Empty

from pyexpat.errors import messages

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import COMMAND_HANDLER_QUEUE_NAME, CENTRAL_CONTROL_SYSTEM_QUEUE_NAME
from src.system.config import SECURITY_MONITOR_QUEUE_NAME
from src.system.config import DEFAULT_LOG_LEVEL, LOG_ERROR, LOG_INFO

import re
from hashlib import sha512

class CommandHandler(BaseCustomProcess):
    """ Модуль обработчика команд """
    log_prefix = "[HANDLER]"
    event_source_name = COMMAND_HANDLER_QUEUE_NAME
    events_q_name = event_source_name

    def __init__(self, queues_dir: QueuesDirectory, log_level: int = DEFAULT_LOG_LEVEL):
        # вызываем конструктор базового класса
        super().__init__(log_prefix=CommandHandler.log_prefix, queues_dir=queues_dir,
                         events_q_name=CommandHandler.event_source_name,
                         event_source_name=CommandHandler.event_source_name,
                         log_level=log_level)
        
        self._log_message(LOG_INFO, f"модуль обработчика команд создан")
        self.users = []
        rights = {'right to create snapshots': True, 'right to correct orbits': True, 'right to edit restrictions on images': True}
        self.users.append(('Admin', 'Admin', rights.copy()))
        rights = {'right to create snapshots': True, 'right to correct orbits': False, 'right to edit restrictions on images': False}
        self.users.append(('Photo', 'Photo', rights.copy()))
        rights = {'right to create snapshots': True, 'right to correct orbits': True, 'right to edit restrictions on images': False}
        self.users.append(('User', 'User', rights.copy()))


    def _check_events_q(self):
        """ Метод проверяет наличие сообщений для данного компонента системы """
        while True:
            try:
                # Получаем сообщение из очереди
                event: Event = self._events_q.get_nowait()

                # Проверяем, что сообщение принадлежит типу Event (см. файл event_types.py)
                if not isinstance(event, Event):
                    return
                
                # Проверяем вид операции и обрабатываем, event.parameters = (имя файла, логин, пароль)
                match event.operation:
                    case 'upload_file':
                        message = event.parameters

                        # if str(sha512((message[0]+message[1]+message[2]).encode('utf-8'))) != message[3]:
                        #     self._log_message(LOG_ERROR, f"Нарушение целостности файла")
                        #     return

                        rights = None
                        for i in range(len(self.users)):
                            if self.users[i][0] == message[1] and self.users[i][1] == message[2]:
                                rights = self.users[i][2]
                                break

                        if rights is not None:
                            file = message[0]
                            list_comands = []
                            for line in file:
                                if line[-1] == '\n':
                                    line = line[:-1]    #отсекаю символ перевода строки
                                if re.match(r'ORBIT -?\d+(?:\.\d*)? -?\d+(?:\.\d*)? -?\d+(?:\.\d*)?$', line):
                                    if rights['right to correct orbits']:
                                        res_split = line.split()
                                        operation = res_split[0]
                                        parameters = res_split[1:]
                                        for i in range(3):
                                            parameters[i] = float(parameters[i])
                                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                                        q.put(
                                        Event(source=self._event_source_name,
                                              destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                                              operation=operation,
                                              parameters=parameters))
                                    else:
                                        self._log_message(LOG_ERROR, 'Ошибка, нет права управления орбитой')
                                elif re.match(r'ADD ZONE -?\d+(?:\.\d*)? -?\d+(?:\.\d*)? -?\d+(?:\.\d*)? -?\d+(?:\.\d*)? -?\d+(?:\.\d*)?$', line):
                                    if rights['right to edit restrictions on images']:
                                        res_split = line.split()
                                        operation = res_split[0] + ' ' + res_split[1]
                                        parameters = res_split[2:]
                                        parameters[0] = int(parameters[0])
                                        for i in range(1, 5):
                                            parameters[i] = float(parameters[i])
                                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                                        q.put(
                                        Event(source=self._event_source_name,
                                              destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                                              operation=operation,
                                              parameters=parameters))
                                    else:
                                        self._log_message(LOG_ERROR, 'Ошибка, нет права изменения хранилища данных')
                                elif re.match(r'REMOVE ZONE d+$', line):
                                    if rights['right to edit restrictions on images']:
                                        res_split = line.split()
                                        operation = res_split[0] + ' ' + res_split[1]
                                        parameters = res_split[2:]
                                        parameters[0] = int(parameters[0])
                                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                                        q.put(
                                        Event(source=self._event_source_name,
                                              destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                                              operation=operation,
                                              parameters=parameters))
                                    else:
                                        self._log_message(LOG_ERROR, 'Ошибка, нет права изменения хранилища данных')
                                elif line == 'MAKE PHOTO':
                                    if rights['right to create snapshots']:
                                        operation = line
                                        parameters = []
                                        q: Queue = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                                        q.put(
                                        Event(source=self._event_source_name,
                                              destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                                              operation=operation,
                                              parameters=parameters))
                                    else:
                                        self._log_message(LOG_ERROR, 'Ошибка, нет права на создание снимков')
                                else:
                                    self._log_message(LOG_ERROR, f"Обработчик команд встретил неизвестную команду")
                                    break

                        else:
                            self._log_message(LOG_ERROR, 'Ошибка авторизации, не правильный логин/пароль')
            except Empty:
                break


    def run(self):
        self._log_message(LOG_INFO, f"модуль обработчик команд активен")

        while self._quit is False:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка системы обработчика команд: {e}")

