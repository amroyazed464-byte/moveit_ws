// Keep one Gazebo transport client alive across the scene worker's requests.
#include <iostream>
#include <string>
#include <gz/msgs/Factory.hh>
#include <gz/transport/Node.hh>

int main()
{
  gz::transport::Node node;
  std::string service, requestType, responseType, timeout, text;
  while (std::getline(std::cin, service) && std::getline(std::cin, requestType) &&
         std::getline(std::cin, responseType) && std::getline(std::cin, timeout) &&
         std::getline(std::cin, text))
  {
    auto request = gz::msgs::Factory::New(requestType, text);
    auto response = gz::msgs::Factory::New(responseType);
    if (!request || !response)
    {
      std::cout << "ERROR\tinvalid protobuf message" << std::endl;
      continue;
    }
    std::string bytes;
    bool result = false;
    bool executed = node.RequestRaw(service, request->SerializeAsString(), requestType,
        responseType, std::stoul(timeout), bytes, result);
    if (executed && result && response->ParseFromString(bytes))
      std::cout << "OK\t" << response->ShortDebugString() << std::endl;
    else
      std::cout << "ERROR\t" << (executed ? "service rejected" : "service timed out") << std::endl;
  }
}
