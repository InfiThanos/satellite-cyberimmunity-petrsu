from multiprocessing import Queue
from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event
from src.system.config import CLIENT_QUEUE_NAME, AUTHORIZATION_CENTER_QUEUE_NAME
from src.system.config import ORBIT_CONTROL_QUEUE_NAME, CENTRAL_CONTROL_SYSTEM_QUEUE_NAME
from src.system.config import DATA_STORAGE_QUEUE_NAME, CAMERA_QUEUE_NAME
from src.system.config import DEFAULT_LOG_LEVEL, LOG_ERROR, LOG_INFO

from hashlib import sha512

class MyAuthorizationCenter(BaseCustomProcess):
    """ Модуль центра авторизации """
    log_prefix = "[AUTHORIZATION]"
    event_source_name = AUTHORIZATION_CENTER_QUEUE_NAME
    events_q_name = event_source_name

    def __init__(self, queues_dir: QueuesDirectory, log_level: int = DEFAULT_LOG_LEVEL):
        # вызываем конструктор базового класса
        super().__init__(log_prefix=MyAuthorizationCenter.log_prefix, queues_dir=queues_dir,
                         events_q_name=MyAuthorizationCenter.event_source_name,
                         event_source_name=MyAuthorizationCenter.event_source_name,
                         log_level=log_level)
        
        self._log_message(LOG_INFO, f"модуль центра авторизации создан")
        self.users = []
        rights = {'right to create snapshots': True, 'right to correct orbits': True, 'right to edit restrictions on images': True}
        self.users.append(('Admin', 'a3ba8f0f793c59723da40d0a86994e8185579895de1431f6781de7a2da2f77ecf3c17bcc3cf5dc22e9095a45567650'
                                    '662f7c6bb2dce83e9fa9025614217e752e', rights.copy()))
        rights = {'right to create snapshots': False, 'right to correct orbits': False, 'right to edit restrictions on images': False}
        self.users.append(('JustUser', 'feafde638ab9bb435c65b577cf2955875d3892dbb7a4f0e88589a6b20c66334936739de008547961637eefc4c2bb1f'
                           '677804e93da9bf9fcb70465c64a81c3900', rights.copy()))
        rights = {'right to create snapshots': True, 'right to correct orbits': False, 'right to edit restrictions on images': False}
        self.users.append(('Photographer', '8046069928ebca01757e7ed38698beb726fe59d9727c3c9c038f29d349cb3c0aeca3d2d88d67aa55414a57ede'
                           '99e285e71f4003079bbb89c68b057d3058f0aed', rights.copy()))
        
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
                    case 'execute commands':
                        q.put(
                        Event(source=self._event_source_name, 
                              destination=CLIENT_QUEUE_NAME, 
                              operation='get username and password', 
                              parameters=None))
                        while(True):
                            while (self._events_q.empty()):    #жду, когда придёт ответ авторизации
                                pass
                            event2: Event = self._events_q.get_nowait()
                            if event2.operation == 'set username and password':
                                rights = None
                                for i in range(len(self.users)):
                                    if self.users[i][0] == event2.parameters[0] and self.users[i][1] == sha512(event2.parameters[1]):
                                        rights = self.users[i][2]
                                        break
                                if rights is not None:
                                    list_command = event.parameters
                                    for command in list_command:
                                        if command[0] == 'ORBIT':
                                            if rights['right to correct orbits']:
                                                q: Queue = self._queues_dir.get_queue(CENTRAL_CONTROL_SYSTEM_QUEUE_NAME)
                                                q.put(
                                                Event(source=self._event_source_name, 
                                                      destination=ORBIT_CONTROL_QUEUE_NAME, 
                                                      operation=command[0], 
                                                      parameters=command[1]))
                                            else:
                                                self._log_message(LOG_ERROR, 'Ошибка, нет права управления орбитой')
                                        elif command[0] == 'ADD ZONE' or command[0] == 'REMOVE ZONE':
                                            if rights['right to edit restrictions on images']:
                                                q: Queue = self._queues_dir.get_queue(CENTRAL_CONTROL_SYSTEM_QUEUE_NAME)
                                                q.put(
                                                Event(source=self._event_source_name, 
                                                      destination=DATA_STORAGE_QUEUE_NAME, 
                                                      operation=command[0], 
                                                      parameters=command[1]))
                                            else:
                                                self._log_message(LOG_ERROR, 'Ошибка, нет права изменения хранилища данных')
                                        elif command[0] == 'MAKE PHOTO':
                                            if rights['right to create snapshots']:
                                                q: Queue = self._queues_dir.get_queue(CENTRAL_CONTROL_SYSTEM_QUEUE_NAME)
                                                q.put(
                                                Event(source=self._event_source_name, 
                                                      destination=CAMERA_QUEUE_NAME, 
                                                      operation=command[0], 
                                                      parameters=command[1]))
                                            else:
                                                self._log_message(LOG_ERROR, 'Ошибка, нет права на создание снимков')
                                        else:
                                            self._log_message(LOG_ERROR, f"Центр авторизации встретил неизвестную команду")
                                else:
                                    self._log_message(LOG_ERROR, 'Ошибка авторизации, не правильный логин/пароль')
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

