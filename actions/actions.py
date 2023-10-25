from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from rasa_sdk.events import UserUtteranceReverted
from rasa_sdk.events import SessionStarted, ActionExecuted
from rasa_sdk.types import DomainDict
from swiplserver import PrologMQI, PrologThread
import json
import os.path
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import datetime

class TelegramAPI():
    
    @staticmethod
    def getMe():
        request = requests.get('https://api.telegram.org/bot5670991553:AAGwyyMvJC4LaWRk7oCDUr3w3Aj5Fz39W0E/getMe').json()  #llamar al api
        if request['ok'] == False:
            print('Hubo un error...')
            print(request['description'])
        else:
        # Llamado a api de telegram, correcto
            return request['result']
    # utilizado para prueba.
    @staticmethod
    def getChatMemberCount(chat_id):
        request = requests.get('https://api.telegram.org/bot5670991553:AAGwyyMvJC4LaWRk7oCDUr3w3Aj5Fz39W0E/getChatMemberCount?chat_id={chat_id}').json()
        if request['ok'] == False:
            print('Hubo un error...')
            print(request['description'])
        else:
        # Llamado a api de telegram, correcto
            return request['result']

class ActionPresentacion(Action):
    #no implementado para grupos
   def name(self) -> Text:
       return "action_presentacion"
   def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
           domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            nombre = next(tracker.get_latest_entity_values("nombre"), None)
            grupo = tracker.get_slot("is_group")
            if not grupo:
                if nombre != None:
                    telegram_user_id = str(tracker.latest_message["metadata"]["message"]["from"]["id"])
                    conocidos = OperarArchivo.cargarArchivo()
                    if telegram_user_id in conocidos:
                    #nada mas para evitar errores, pero supuse el id ya se encuentra en "conocidos"
                        conocidos[telegram_user_id]['name_set']= True
                        #si ya habia dicho su nombre, entonces name_set ya estaba en true, pero lo reescribo,al igual que el nombre.
                        conocidos[telegram_user_id]['name']= nombre
                        OperarArchivo.guardar(conocidos)
                    return [SlotSet("name",nombre),SlotSet("logged_in",True)]

class ActionCursando(Action):
    def name(self) -> Text:
        return "action_cursando"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text,Any]) -> List[Dict[Text,Any]]:
        with PrologMQI(port=8000) as mqi:
            with mqi.create_thread() as prolog_thread:
                prolog_thread.query_async("consult('C:/Rasa_Projects/rasa_project_nuevo/actions/base_datos_prolog.pl')", find_all=False)
                prolog_thread.query_async(f"cursando(X).", find_all=False)
                result = prolog_thread.query_async_result()
                # me devuelve una lista de python, con 1 elemento "X" que es otra lista, con todas las materias q curso
                # otra manera seria, que no esten en una lista, sino que sean hechos, y en python itero, y devuelve uno por uno.
                aList = result[0]
                if len(aList['X']) > 0:
                    Laux1 = str(aList['X'][0])
                    prolog_thread.query_async(f"materia({Laux1},Z,_,_)")
                    result = prolog_thread.query_async_result()
                    print(result)
                    cursando = str(result[0]['Z'])
                    for i in range(1,len(aList['X'])):
                        Laux2 = str(aList['X'][i])
                        prolog_thread.query_async(f"materia({Laux2},Y,_,_)")
                        result = prolog_thread.query_async_result()
                        materiaaux = str(result[0]['Y'])
                        cursando = cursando + ', ' + materiaaux
                    dispatcher.utter_message(text=f'{"estoy cursando " + cursando}')
                else:
                        dispatcher.utter_message(text=f'{"no estoy cursando nada"}')

class ActionCursandoYear(Action):
    def name(self) -> Text:
        return "action_cursando_year"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text,Any]) -> List[Dict[Text,Any]]:
            year = next(tracker.get_latest_entity_values("year"), None)
            with PrologMQI(port=8000) as mqi:
                with mqi.create_thread() as prolog_thread:
                    prolog_thread.query_async("consult('C:/Rasa_Projects/rasa_project_nuevo/actions/base_datos_prolog.pl')", find_all=False)
                    prolog_thread.query_async(f"cursando(X).", find_all=False)
                    result = prolog_thread.query_async_result()
                    # me devuelve una lista de python, con 1 elemento "X" que es otra lista, con todas las materias q curso
                    # otra manera seria, mas facil en python, pero mas difcil en prolog, q devuelva por backtracking 1 x 1
                    aList = result[0]
                    if len(aList['X']) > 0:
                        cursando ="estoy cursando "
                        Laux1 = str(aList['X'][0])
                        c = 0       #lo uso despues, para que la primera materia q imprima no le ponga la ','
                        for i in range(0,len(aList['X'])):
                            Laux2 = str(aList['X'][i])
                            prolog_thread.query_async(f"materia({Laux2},Y,{year},_)")
                            result = prolog_thread.query_async_result()
                            if result != False:
                                materiaaux = str(result[0]['Y'])
                                if c != 1:
                                    cursando = cursando +' ' + materiaaux
                                    c = 1
                                else:
                                    cursando = cursando + ',' + materiaaux
                        if cursando == "estoy cursando ":
                                dispatcher.utter_message(text=f'{"no estoy cursando ninguna de ese año"}')
                        else:
                            dispatcher.utter_message(text=f'{cursando}')
                    else:
                            dispatcher.utter_message(text=f'{"no estoy cursando ninguna"}')

class OperarArchivo():

    @staticmethod
    def guardar(AGuardar):
        with open(".\\actions\\conocidos","w") as archivo_descarga:
            json.dump(AGuardar, archivo_descarga, indent=4)
        archivo_descarga.close()

    @staticmethod
    def cargarArchivo(): 
        if os.path.isfile(".\\actions\\conocidos"):
            with open(".\\actions\\conocidos","r") as archivo_carga:
                retorno=json.load(archivo_carga)
                archivo_carga.close()
        else:
            retorno={}
        return retorno

# class ActionExtraerConocidos(Action):
#     def name(self) -> Text:
#        return "action_extraer_conocidos"
#     def run(self, dispatcher: CollectingDispatcher,tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         name_surname = tracker.get_slot("name")#agregar apellido
#         conocidos= OperarArchivo.cargarArchivo()
#         if name_surname in conocidos:
#             if conocidos[name_surname]['profe'] == True:
#                 if name_surname == "analia":
#                     dispatcher.utter_message(text=f"la profesora de exploratoria?")
#                 else:
#                     dispatcher.utter_message(text=f"el profesor de exploratoria?")
#             elif conocidos[name_surname]['ayudante'] == True:
#                 dispatcher.utter_message(text=f"el ayudante de exploratoria?")
#         else:
#             nombre = next(tracker.get_latest_entity_values("nombre"), None)
#             conocidos[name_surname]={}
#             conocidos[name_surname]['nombre']=nombre
#             conocidos[name_surname]['profe']=False
#             conocidos[name_surname]['ayudante']=False
#             OperarArchivo.guardar(conocidos)
#         return []

class MoodUsuarioDado(Action):
    def name(self) -> Text:
        return "action_user_mood"
    def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            #no funciona en grupos
            intent =  tracker.latest_message['intent'].get('name')
            if intent == 'mood_feliz' or 'mood_triste':
                return [SlotSet("user_mood_set",True)]
            else:
                return [SlotSet("user_mood_set",False)]

class MoodUsuarioPregMood(Action):
     def name(self) -> Text:
         return "action_bot_mood_asked"
     def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            asked= next(tracker.get_latest_entity_values("bot_mood_asked"), None)
            if asked == 'vos':
                dispatcher.utter_message(response = "utter_como_estoy")

class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"
    async def run(
      self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        #print(tracker.latest_message["metadata"])
        print('hola')
        #Si es grupo:
        if (tracker.latest_message["metadata"]["message"]["chat"]["type"] == 'group') or (tracker.latest_message["metadata"]["message"]["chat"]["type"] == 'supergroup'):
            chat_id = tracker.latest_message["metadata"]["message"]["chat"]["id"]
            #N = TelegramAPI.getChatMemberCount(chat_id)
            #cantidad = N
            cantidad = 3
            print('cantidad:',cantidad)
            #slot CantUsersConfirmed se inicia en 0 (aclarado en domain.yml)
            return [SessionStarted(), ActionExecuted("action_listen"),SlotSet("is_group",True),SlotSet("CantUsers",cantidad)]
        else:
            print('saru')
            conocidos = OperarArchivo.cargarArchivo()
            telegram_user_id = str(tracker.latest_message["metadata"]["message"]["from"]["id"])
            ## pruebo pasando a string..
            if telegram_user_id in conocidos:
                conocidos[telegram_user_id]['first_time'] = False
                if conocidos[telegram_user_id]['name_set'] == True :
                    nombre = conocidos[telegram_user_id]['name']
                else:
                    nombre = tracker.latest_message["metadata"]["message"]["from"]["first_name"]
            else:
                print('ola')
                conocidos[telegram_user_id] = {}
                conocidos[telegram_user_id]['name_set'] = False
                conocidos[telegram_user_id]['first_time'] = True
                nombre = tracker.latest_message["metadata"]["message"]["from"]["first_name"]
            OperarArchivo.guardar(conocidos)
            return [SessionStarted(), ActionExecuted("action_listen"),SlotSet("is_group",False),SlotSet("name",nombre),SlotSet("logged_in",True),SlotSet("user_mood_set",False)]
            # Ademas SlotSet de logged_in, y user_mood_set

class PrimerSaludo(Action):
    def name(self) -> Text:
        return "action_primer_saludo"
    def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            # no funciona en grupos
            grupo = tracker.get_slot("is_group")
            if not grupo:
                print('no grupo')
                intent =  tracker.latest_message['intent'].get('name')
                if intent == 'saludo':
                    print('intent saludo')
                    telegram_user_id = str(tracker.latest_message["metadata"]["message"]["from"]["id"])
                    conocidos = OperarArchivo.cargarArchivo()
                    nombre = tracker.get_slot("name")
                    print(nombre)
                    print(telegram_user_id)
                    if telegram_user_id in conocidos:
                        print('esta en conocidos')
                        if conocidos[telegram_user_id]['first_time'] == False:
                            dispatcher.utter_message(text=f"Hola denuevo {nombre}!")
                        else:
                            dispatcher.utter_message(text=f"Hola {nombre}! Soy Rambot, el asistente virtual de Adriel Ferrero")
                    OperarArchivo.guardar(conocidos)

class ExtraeHorario():
    # horario en formato: 2015-01-26T06:00:00.000-02:00 (Del duckling entity extractor)
    @staticmethod
    def mes(fecha):
        month = fecha.split("T")
        month = month[0].split("-")
        month = month[1]
        return month
    @staticmethod
    def dia(fecha):
        day = fecha.split("T")
        day = day[0].split("-")
        day = day[2]
        return day
    @staticmethod
    def hora(fecha):
        hour = fecha.split("T")
        hour = hour[1].split(":")
        hour = hour[0]
        return hour

class MapearHorario():    
    # esta action tiene en cuenta la posibilidad de que un integrante del grupo complemente un horario
    # (ej: uno dijo mes y dia, y este dice la hora)
    # mapea horario obtenido recientemente, dependiendo el horario ya guardado (ultima propueta, guardada en slots)
    # Supone si la persona dijo solo dia( y no mes) se refirio a este mes. (a menos la ultima propuesta incluya mes)
    # Supone si la persona dijo solo hora ( y no mes/dia) se refiere a la proxima (a menos la ultima propuesta incluya algunos de estos datos)
    @staticmethod
    #class method seria si modifica la clase, y el otro no me lo acuerdo
    # NO SE SI PUEDO HACER DESDE ACA, UN RETURN: opcion: paso cuales de los 3 slots les paso su valor
    # o hago esto en cada extract_slot mas facil (no importa quede largo)
    def MapeaHoraRecibida(horario,mes,dia):
        # NO USADA, ESTE MISMO CODIGO, SE REPITA EN EXTRACT_SLOT DE HORA,DIA Y MES
        pos = 0
        length = len(horario)
        print(length)
        i = 0
        while (i < length) and (horario[pos]['extractor'] != 'DucklingEntityExtractor'):
            pos += 1
        print(pos)
        if i < length:
        #si la entity se encuentra en el ultimo mensaje, sino, no hago nada.
            info = horario[pos]['additional_info']['grain']
            if info == 'month':
                month = ExtraeHorario.mes(horario[pos]['value'])
                return {"mes": month}
            if info == 'day':
                #obtengo slot mes, y si no estaba seteado, lo seteo con el obtenido ahora.
                day = ExtraeHorario.dia(horario[pos]['value'])
                if mes == None:
                    month = ExtraeHorario.mes(horario[pos]['value'])
                    return {"mes": month, "dia":day}
                else:
                    return {"dia":day}
            if (info == 'hour') or (info == 'minute'):
                hour = ExtraeHorario.hora(horario[pos]['value'])
                if mes == None:
                    month = ExtraeHorario.mes(horario[pos]['value'])
                    if dia == None:
                        day = ExtraeHorario.dia(horario[pos]['value'])
                        return {"mes": month, "dia":day,"hora":hour}
                    else:
                        return {"mes": month, "hora":hour}
                else:
                    if dia == None:
                        day = ExtraeHorario.dia(horario[pos]['value'])
                        return {"dia":day, "hora":hour}
                    else:
                        return {"hora":hour}

class MuestraEventosCalendarioGoogle(Action):
    def name(self) -> Text:
        return "action_muestra_eventos"
    def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            mes = tracker.get_slot("mes")
            dia = tracker.get_slot("dia")
            hora = tracker.get_slot("hora")
            creds = None
            SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']#calendar.readonly porq solo voy a leer
            # el archivo token.json almacena el acceso del usuario y actualiza tokens, 
            #  es creada automaticamente cuando la actualizacion del flow se completa
            # por primera vez
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            # si no hay credenciales validas disponibles, el usuario loguea.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        ".\\actions\\credentials.json", SCOPES)
                    creds = flow.run_local_server(port=0)
                # Guarda las credenciales para la proxima ejecucion
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

            try:#bloque que si no da error, lo ejecuta
                service = build('calendar', 'v3', credentials=creds)

                # Llamo a la API del calendario
                now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indica UTC tiempo (cambiar utc)
                #si quiero dar los horarios ocupados de cierto dia:
                #horariomin = datetime.datetime(2022,mes,dia).isoformat()
                #horariomax = datetime.datetime(2022,mes,dia,23,59).isoformat()
                print('Mis horarios ocupados son:')
                events_result = service.events().list(calendarId='d5f9f6052fffdb67cd18405f31e9bb9ab028678ce3128484d2a8239a51f49bc8@group.calendar.google.com', timeMin=now,
                                                    maxResults=1000, singleEvents=True,#1000 EVENTOS PROXIMOS, que sobre.
                                                    orderBy='startTime').execute()
                events = events_result.get('items', [])

                if not events:
                    print('No upcoming events found.')
                    return

                # Imprime los siguientes 10 eventos CAMBIAR FORAMTO DE COMO IMPRIME HORA, Q SE VEA MAS NATURAL
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    print(start, event['summary'])

            except HttpError as error:
                print('An error occurred: %s' % error)

class CrearEventoCalendarioGoogle(Action):
    def name(self) -> Text:
        return "action_crea_evento"
    def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            mes = tracker.get_slot("mes")
            dia = tracker.get_slot("dia")
            hora = tracker.get_slot("hora")
            creds = None
            if (mes != None) and (dia != None) and (hora != None):
                SCOPES = ['https://www.googleapis.com/auth/calendar']#permiso para modificar todo calendario
                #calendar.events para poder crear eventos
                # el archivo token.json almacena el acceso del usuario y actualiza tokens, 
                #  es creada automaticamente cuando la actualizacion del flow se completa
                # por primera vez
                if os.path.exists('token.json'):
                    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                # si no hay credenciales validas disponibles, el usuario loguea.
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            ".\\actions\\credentials.json", SCOPES)
                        creds = flow.run_local_server(port=0)
                    # Guarda las credenciales para la proxima ejecucion
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())

                try:#bloque que si no da error, lo ejecuta
                    service = build('calendar', 'v3', credentials=creds)
                    #a esta action solo debe entrar cuano tenga todos los slots llenos, por ende ni pregunto su valor
                    start = datetime.datetime(2022,mes,dia,hora).isoformat()#PARA PODER PONER MINUTOS, MODIFICAR MAPEADO DE HORARIO, Y separar la hora de los minutos 
                    end = datetime.datetime(2022,mes,dia,hora+1).isoformat()# por ahora, solo se puede una hora en punto. Tambien asumo el evento dura 1 hora
                    event_result = service.events().insert(calendarId='d5f9f6052fffdb67cd18405f31e9bb9ab028678ce3128484d2a8239a51f49bc8@group.calendar.google.com',
                        body={
                        "summary": 'EventoRasa',
                        "description": 'Evento de chatbot',
                        "start": {"dateTime": start, "timeZone": 'America/Argentina/Buenos_Aires'},
                        "end": {"dateTime": end, "timeZone": 'America/Argentina/Buenos_Aires'},
                    }
            ).execute()
                    dispatcher.utter_message(text=f"Buenisimo! nos vemos el {dia} a las {hora} entonces")
                    # no aclaro mes, se entiende igual
                    # si dia = hoy deberia no decirlo..
                except HttpError as error:
                    print('An error occurred: %s' % error)
            else:
                print('algun slot de crear_evento esta en None')
                
class ValidarForm(FormValidationAction):
    #slot_value es el valor que tomara el slot, luego de validarlo (valor temporal, se valida antes de mapearlo al slot)
    def name(self) -> Text:
        return "validate_evento_form"
    def validate_hora(    
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
            #por como implemente el mapeado de horario, se que cuando se llene el slot hora, ya tengo todos los slots.
            # es valido si: en mi calendario de google no hay nada q se interponga.
            # tiene en cuenta si los eventos son de mas de 1 hora ( suponiendo eventos en el calendario de mas de 1 hora,
            #   ,agregados por un humano, ya que el bot agrega solo de 1 hora)
            mes = tracker.get_slot("mes")
            dia = tracker.get_slot("dia")
            hora = slot_value
            print('mes:',mes)
            print('dia:',dia)
            print('hora:',hora)
            creds = None
            if (mes != None) and (dia != None) and (slot_value != None):
                SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']#calendar.readonly porq solo voy a leer
                # el archivo token.json almacena el acceso del usuario y actualiza tokens, 
                #  es creada automaticamente cuando la actualizacion del flow se completa
                # por primera vez
                if os.path.exists('token.json'):
                    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                # si no hay credenciales validas disponibles, el usuario loguea.
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            ".\\actions\\credentials.json", SCOPES)
                        creds = flow.run_local_server(port=0)
                    # Guarda las credenciales para la proxima ejecucion
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())

                try:#bloque que si no da error, lo ejecuta
                    service = build('calendar', 'v3', credentials=creds)

                    horariomin = datetime.datetime(2022,mes,dia,00,00).isoformat()
                    horariomax = datetime.datetime(2022,mes,dia,23,59).isoformat()
                    print('Mis horarios ocupados son:')
                    events_result = service.events().list(calendarId='d5f9f6052fffdb67cd18405f31e9bb9ab028678ce3128484d2a8239a51f49bc8@group.calendar.google.com', timeMax=horariomax, timeMin=horariomin,
                                                        maxResults=1000, singleEvents=True,#1000 EVENTOS PROXIMOS, que sobre.
                                                        orderBy='startTime').execute()
                    events = events_result.get('items', [])

                    if not events:
                        print('No hay eventos')
                        dispatcher.utter_message(text=f"Yo puedo")
                        return{"hora":slot_value}

                    Puedo = True
                    for event in events:
                        if Puedo == True:
                            # para cada evento fijarme si interviene con el horario dado 
                            inicial = event['start'].get('dateTime')
                            final = event['end'].get('dateTime')
                            # de todos modos, solo crea eventos de 1 hora.
                            if inicial < hora :
                                if final > hora:
                                    Puedo = False
                            elif inicial > hora :
                                if inicial < (hora + 1) :
                                    Puedo = False
                            else:
                                #inicia al mismo tiempo que otro evento
                                Puedo = False
                    if Puedo == True:
                        dispatcher.utter_message(text=f"Yo puedo")
                        return{"hora":slot_value}
                    else:
                        dispatcher.utter_message(text=f"Yo no puedo")
                        # reiniciar todos los slots (horario invalido)
                        return {"mes": None, "dia":None, "hora":None, "UsersConfirmed":None}

                except HttpError as error:
                    print('Ocurrio un error: %s' % error)
            else:
                print('validar horario, algun slot en None')
    
    async def extract_mes(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        last_intent = tracker.latest_message['intent'].get('name')
        if last_intent == 'propone_reunion':
            horario = tracker.latest_message['entities']
            mes = tracker.get_slot("mes")
            dia = tracker.get_slot("dia")
            print('extract_mes')
            length = len(horario) 
            print('length:',length)
            print('lista: ',horario)
            pos = 0
            print(horario[pos]['extractor'])
            while (pos < length) and (horario[pos]['extractor'] != 'DucklingEntityExtractor'):
                pos += 1
            print('pos:',pos)
            if pos < length:
            #si la entity se encuentra en el ultimo mensaje, sino, no hago nada.
                info = horario[pos]['additional_info']['grain']
                print ('info:',info)
                if info == 'month':
                    month = ExtraeHorario.mes(horario[pos]['value'])
                    return {"mes": month}
                #info valdria 'month' pues es extract_mes
                if info == 'day':
                    #obtengo slot mes, y si no estaba seteado, lo seteo con el obtenido ahora.
                    day = ExtraeHorario.dia(horario[pos]['value'])
                    if mes == None:
                        month = ExtraeHorario.mes(horario[pos]['value'])
                        return {"mes": month, "dia":day}
                    else:
                        return {"dia":day}
                if (info == 'hour') or (info == 'minute'):
                    hour = ExtraeHorario.hora(horario[pos]['value'])
                    if mes == None:
                        month = ExtraeHorario.mes(horario[pos]['value'])
                        if dia == None:
                            day = ExtraeHorario.dia(horario[pos]['value'])
                            return {"mes": month, "dia":day,"hora":hour}
                        else:
                            return {"mes": month, "hora":hour}
                    else:
                        if dia == None:
                            day = ExtraeHorario.dia(horario[pos]['value'])
                            return {"dia":day, "hora":hour}
                        else:
                            return {"hora":hour}
        else:
            return{"mes":None}

    async def extract_dia(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        last_intent = tracker.latest_message['intent'].get('name')
        if last_intent == 'propone_reunion':
            horario = tracker.latest_message['entities']
            mes = tracker.get_slot("mes")
            dia = tracker.get_slot("dia")
            pos = 0
            print('extract_dia')
            length = len(horario) 
            print('length:',length)
            #print('horario:',horario)
            i = 0
            while (pos < length) and (horario[pos]['extractor'] != 'DucklingEntityExtractor'):
                pos += 1
            print('pos:',pos)
            if pos < length:
            #si la entity se encuentra en el ultimo mensaje, sino, no hago nada.
                info = horario[pos]['additional_info']['grain']
                print ('info:',info)
                if info == 'month':
                    month = ExtraeHorario.mes(horario[pos]['value'])
                    return {"mes": month}
                if info == 'day':
                    #obtengo slot mes, y si no estaba seteado, lo seteo con el obtenido ahora.
                    day = ExtraeHorario.dia(horario[pos]['value'])
                    if mes == None:
                        month = ExtraeHorario.mes(horario[pos]['value'])
                        return {"mes": month, "dia":day}
                    else:
                        return {"dia":day}
                if (info == 'hour') or (info == 'minute'):
                    hour = ExtraeHorario.hora(horario[pos]['value'])
                    if mes == None:
                        month = ExtraeHorario.mes(horario[pos]['value'])
                        if dia == None:
                            day = ExtraeHorario.dia(horario[pos]['value'])
                            return {"mes": month, "dia":day,"hora":hour}
                        else:
                            return {"mes": month, "hora":hour}
                    else:
                        if dia == None:
                            day = ExtraeHorario.dia(horario[pos]['value'])
                            return {"dia":day, "hora":hour}
                        else:
                            return {"hora":hour}
        else:
            return{"dia":None}

    async def extract_hora(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        last_intent = tracker.latest_message['intent'].get('name')
        if last_intent == 'propone_reunion':
            horario = tracker.latest_message['entities']
            mes = tracker.get_slot("mes")
            dia = tracker.get_slot("dia")
            pos = 0
            print ('extact_hora')
            length = len(horario) 
            print('length',length)
            i = 0
            while (pos < length) and (horario[pos]['extractor'] != 'DucklingEntityExtractor'):
                pos += 1
            print('pos:',pos)
            if pos < length:
            #si la entity se encuentra en el ultimo mensaje, sino, no hago nada.
                info = horario[pos]['additional_info']['grain']
                print ('info:',info)
                if info == 'month':
                    month = ExtraeHorario.mes(horario[pos]['value'])
                    return {"mes": month}
                if info == 'day':
                    #obtengo slot mes, y si no estaba seteado, lo seteo con el obtenido ahora.
                    day = ExtraeHorario.dia(horario[pos]['value'])
                    if mes == None:
                        month = ExtraeHorario.mes(horario[pos]['value'])
                        return {"mes": month, "dia":day}
                    else:
                        return {"dia":day}
                if (info == 'hour') or (info == 'minute'):
                    hour = ExtraeHorario.hora(horario[pos]['value'])
                    if mes == None:
                        month = ExtraeHorario.mes(horario[pos]['value'])
                        if dia == None:
                            day = ExtraeHorario.dia(horario[pos]['value'])
                            return {"mes": month, "dia":day,"hora":hour}
                        else:
                            return {"mes": month, "hora":hour}
                    else:
                        if dia == None:
                            day = ExtraeHorario.dia(horario[pos]['value'])
                            return {"dia":day, "hora":hour}
                        else:
                            return {"hora":hour}
        else:
            return{"hora":None}
        
    async def extract_UsersConfirmed(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
            cantidad = tracker.get_slot("CantUsers")
            confirmados = tracker.get_slot("CantUsersConfirmed")
            print('cantidad:',cantidad)
            print('confirmados:',confirmados)
            if (cantidad != None) and (confirmados != None):
                if  confirmados >= (cantidad/2 + 1):
                    return{"UsersConfirmed": 1}
                else:
                    return{"UsersConfirmed":None}
            else:
                print('alguno de estos slotes tiene el valor None')

# crear validate del USersConfirmed, innecesario pero probar a ver si el ciclo se corta

class ActionAskUsersConfirmed(Action):
    # se llama cuando se requiere este slot.
    # anterior a esto, se valido el slot, y no estaba cargado (None) entonces el form llama esta action
    # si no se valida, el bot espera a q confirme la mayoria de personas.
    def name(self):
        return 'action_ask_UsersConfirmed'
    def run(self, dispatcher, tracker, domain):
        return [ActionExecuted("action_listen")]
    #el action_listen será la causa del loop?
        
    
class ReseteaSlotsFormEvento(Action):
    def name(self) -> Text:
        return "action_reset_event_slots"
    def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            # resetea slots: mes,dia,hora y UsersConfirmed
            print('Slots del form reseteados!')
            return (SlotSet("mes",None),SlotSet("dia",None),SlotSet("hora",None),SlotSet("UsersConfirmed",None))
            

class UserConfirmaEvento(Action):
     def name(self) -> Text:
         return "action_usuario_puede"
     def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            confirmados = tracker.get_slot("CantUsersConfirmed") + 1
            print('confirmados:',confirmados)
            return (SlotSet("CantUsersConfirmed",confirmados))