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

`CreateMessage` attachment limits are inclusive: 0–50 attachment children and
at most 100 MiB of decoded attachment bytes in the synthetic adapter profile.
The SOAP count fault is raised during wire parsing, before normalization; the
decoded-byte check is applied while normalizing attachment content. The raw
SOAP XML request remains subject to the separate 100 MiB wire-size limit.

SOAP 1.1 faults contain a stable error code, safe message, request ID, and
correlation ID. Raw XML, upstream fault bytes, and normalized adapter results
remain separate in `SoapExchange`. `/isds/ws2` is reserved for the pinned
large-message profile and rejects this standard operation matrix.
