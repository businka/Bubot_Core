from bubot.OcfResource.OcfResource import OcfResource


class OicRCoapCloudConf(OcfResource):
    async def _on_post(self, request, payload, response):
        result = await super()._on_post(request, payload, response)
        self.device.log.info(self.payload)
        self.device.save_config()
        return result
