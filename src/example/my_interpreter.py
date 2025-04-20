from multiprocessing import Queue
from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import INTERPRETER_QUEUE_NAME, AUTHORIZATION_CENTER_QUEUE_NAME
from src.system.config import ORBIT_CONTROL_QUEUE_NAME, DEFAULT_LOG_LEVEL, LOG_ERROR, LOG_INFO

import re

class MyInterpreter(BaseCustomProcess):
    """ Модуль интерпретатора """
    log_prefix = "[INTERPRETER]"
    event_source_name = INTERPRETER_QUEUE_NAME
    events_q_name = event_source_name

    def __init__(self, queues_dir: QueuesDirectory, log_level: int = DEFAULT_LOG_LEVEL):
        # вызываем конструктор базового класса
        super().__init__(log_prefix=MyInterpreter.log_prefix, queues_dir=queues_dir,
                         events_q_name=MyInterpreter.event_source_name,
                         event_source_name=MyInterpreter.event_source_name,
                         log_level=log_level)
        
        self._log_message(LOG_INFO, f"модуль интерпретатора создан")


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
                    case 'upload_file':
                        flag_error = False
                        name_file = event.parameters
                        try:
                            with open(name_file, 'r') as f:
                                list_comands = []
                                for line in f:
                                    if line[-1] == '\n':
                                        line = line[:-1]    #отсекаю символ перевода строки
                                    if re.match(r'ORBIT \d+\.\d+ \d+\.\d+ \d+\.\d+$', line):
                                        res_split = line.split()
                                        operation = res_split[0]
                                        parameters = res_split[1:]
                                        for i in range(3):
                                            parameters[i] = float(parameters[i])
                                        list_comands.append((operation, parameters))
                                    elif re.match(r'ADD ZONE d+ \d+\.\d+ \d+\.\d+ \d+\.\d \d+\.\d+$', line):
                                        res_split = line.split()
                                        operation = res_split[0] + ' ' + res_split[1]
                                        parameters = res_split[2:]
                                        parameters[0] = int(parameters[0])
                                        for i in range(1, 5):
                                            parameters[i] = float(parameters[i])
                                        list_comands.append((operation, parameters))
                                    elif re.match(r'REMOVE ZONE d+$', line):
                                        res_split = line.split()
                                        operation = res_split[0] + ' ' + res_split[1]
                                        parameters = res_split[2:]
                                        parameters[0] = int(parameters[0])
                                        list_comands.append((operation, parameters))
                                    elif line == 'MAKE PHOTO':
                                        operation = line
                                        parameters = []
                                        list_comands.append((operation, parameters))
                                    else:
                                        flag_error = True
                                        self._log_message(LOG_ERROR, f"Интерпретатор встретил неизвестную команду")
                                        break
                                if not flag_error:
                                    q: Queue = self._queues_dir.get_queue(AUTHORIZATION_CENTER_QUEUE_NAME)
                                    q.put(
                                    Event(source=self._event_source_name, 
                                          destination=AUTHORIZATION_CENTER_QUEUE_NAME, 
                                          operation='execute commands', 
                                          parameters=list_comands))
                        except IOError:
                            self._log_message(LOG_ERROR, f"Указанный файл команд не найден")          
            except Empty:
                break


    def run(self):
        self._log_message(LOG_INFO, f"модуль интерпретатора активен")

        while self._quit is False:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка системы интерпретатора: {e}")
