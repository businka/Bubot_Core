import json
import uuid

from py4j.java_gateway import JavaGateway, GatewayParameters


class JasperReport:
    data_dir = "./jasper_reports"
    address = '192.168.1.28'

    def pdf_from_json(self, report, data):
        gateway = JavaGateway(
            gateway_parameters=GatewayParameters(address=self.address),
        )
        uid = str(uuid.uuid4())
        with open('{0}/request/{1}.json'.format(self.data_dir, uid), 'w') as file:
            json.dump(data, file)
        gateway.entry_point.pdf_from_json(report, uid)
        return uid
