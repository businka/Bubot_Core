"""
Bit Writing Request/Response
------------------------------

TODO add ExtException to protocol
"""
from bubot.coap import Message, Code
import asyncio
from bubot.OcfMessage import OcfRequest, OcfResponse
from bubot.ExtException import ExtException
import logging

# _logger = logging.getLogger('CoapProtocol')


class CoapProtocol:
    def __init__(self, server, **kwargs):
        # self.loop = loop
        self.transport = None
        self.server = server
        self.log = server.device.log
        self.multicast = kwargs.get('multicast', False)
        # self.on_con_made = loop.create_future()
        # self.on_con_lost = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        # self.on_con_made.set_result(True)

    def datagram_received(self, data, remote):
        try:
            # self.log.debug(remote[1])
            message = Message.decode(data, remote)
        except Exception as e:
            logging.warning('datagram message encoding: {0} from {1}'.format(e, remote[0]))
            return
        code = message.code
        if code.is_request():
            handler_name = 'on_{0}'.format(code.name.lower())
            if not hasattr(self, handler_name):
                self.log.warning('handler not found {}'.format(handler_name))
                return
            try:
                message = OcfRequest.decode_from_coap(message, self.multicast)
            except Exception as e:
                logging.warning('OcfRequest message encoding: {0} from {1}'.format(e, remote[0]))
                return
            try:
                self.log.debug('{0} {1}'.format(
                    handler_name,
                    message.mid
                ))
                self.server.loop.create_task(getattr(self, handler_name)(message))
            except Exception as err:
                # self.server.devices.log.error('{0} {1}'.format(handler, e))
                answer = Message.generate_error(err, message)
                self.server.send_message(answer, remote)
                self.log.error(err)

        else:
            try:
                answer = self.server.answer[message.token]
            except KeyError:
                self.log.warning('request not found token={0} href={1} remote={2}'.format(
                    message.token, message.opt.uri_path, message.remote))  # надо сделать отбивку неожидаемых ответов
                return
            try:
                message = OcfResponse.decode_from_coap(message, self.multicast)
            except Exception as e:
                logging.warning('OcfResponse message encoding: {0} from {1}'.format(e, remote[0]))
                return

            if asyncio.isfuture(answer['response']):
                if code.is_successful():
                    self.log.debug('response {0}'.format(
                        message.token
                    ))
                    answer['response'].set_result(message)
                else:
                    self.log.debug('exception {0}'.format(
                        message.token
                    ))
                    answer['response'].set_exception(Exception(message.cn))
                return
            elif callable(answer['response']):
                try:
                    self.log.debug('long response {0}'.format(
                        message.token
                    ))
                    self.server.loop.create_task(answer['response'](message, answer))
                except Exception as err:
                    self.log.error(err)
            # if isinstance(answer['response'], list):
            #     answer['response'].append(message)

        # self.server.bridge.on_datagram_received(data, addr)

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Connection closed")
        # self.on_con_lost.set_result(True)

    # async def on_content(self, message):
    #     try:
    #         answer = self.server.answer[message.mid]
    #     except KeyError:
    #         self.log.warning('request not found')
    #         return
    #     if asyncio.isfuture(answer['response']):
    #         answer['response'].set_result(message)
    #         return
    #     answer.append(message)

    async def on_get(self, message):
        try:
            answer_data = await self.server.device.on_get_request(message)
            answer = OcfResponse.generate_answer(answer_data, message)
            await self.server.send_answer(answer)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            # self.server.devices.log.error('{0} {1}'.format(handler, e))
            self.log.error('on_get {0} {1} {2}: {3}'.format(
                self.server.device.__class__.__name__,
                message.operation,
                message.to.href,
                err))
            answer = OcfResponse.generate_error(err, message)
            await self.server.send_answer(answer)

    async def on_post(self, message):
        try:
            answer_data = await self.server.device.on_post_request(message)
            answer = OcfResponse.generate_answer(answer_data, message, code=Code.CHANGED)
            await self.server.send_answer(answer)
        except Exception as err:
            # self.server.devices.log.error('{0} {1}'.format(handler, e))
            self.log.error('on_post {0} {1} {2}: {3}'.format(
                self.server.device.__class__.__name__,
                message.operation,
                message.to.href,
                err))
            answer = OcfResponse.generate_error(err, message)
            await self.server.send_answer(answer)
