# Synthetic ISDS SOAP operation matrix

This is a versioned, offline compatibility profile implemented by
`ag_datovka.soap_gateway.SyntheticSoapGateway`; it is not a live ISDS service
or an official WSDL.

| Operation | SOAPAction | Endpoint | Request sequence |
|---|---|---|---|
| Authenticate | `urn:isds:Authenticate` | `/isds/ws` | `requestId, login` |
| CreateMessage | `urn:isds:CreateMessage` | `/isds/ws` | `messageId, subject, recipientBoxId, attachments` |
| GetMessage | `urn:isds:GetMessage` | `/isds/ws` | `messageId` |
| GetListOfMessages | `urn:isds:GetListOfMessages` | `/isds/ws` | `boxId, from, to` |
| GetMessageStateChanges | `urn:isds:GetMessageStateChanges` | `/isds/ws` | `boxId, from, to` |
| GetDeliveryInfo | `urn:isds:GetDeliveryInfo` | `/isds/ws` | `messageId` |
| GetOwnerInfo | `urn:isds:GetOwnerInfo` | `/isds/ws` | `boxId` |
| GetUserInfo | `urn:isds:GetUserInfo` | `/isds/ws` | `userId` |

SOAP 1.1 faults contain a stable error code, safe message, request ID, and
correlation ID. Raw XML, upstream fault bytes, and normalized adapter results
remain separate in `SoapExchange`. `/isds/ws2` is reserved for the pinned
large-message profile and rejects this standard operation matrix.
