// Harmonic's visual_config changes colors only. Recreate screen visuals for texture changes.
#include <map>
#include <mutex>
#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/visual.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/Conversions.hh>
#include <gz/sim/SdfEntityCreator.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Geometry.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/ParentEntity.hh>
#include <gz/sim/components/Pose.hh>
#include <gz/sim/components/Visual.hh>
#include <gz/transport/Node.hh>

namespace heritage_tour
{
class ScreenSystem : public gz::sim::System,
                     public gz::sim::ISystemConfigure,
                     public gz::sim::ISystemPreUpdate
{
  public: void Configure(const gz::sim::Entity &,
      const std::shared_ptr<const sdf::Element> &,
      gz::sim::EntityComponentManager &, gz::sim::EventManager &_events) override
  {
    this->events = &_events;
    this->node.Advertise("/world/heritage_hall/tour_texture", &ScreenSystem::Texture, this);
  }

  public: bool Texture(const gz::msgs::Visual &_request, gz::msgs::Boolean &_reply)
  {
    std::lock_guard<std::mutex> lock(this->mutex);
    this->pending[_request.name()] = _request.material();
    _reply.set_data(true);
    return true;
  }

  public: void PreUpdate(const gz::sim::UpdateInfo &,
      gz::sim::EntityComponentManager &_ecm) override
  {
    std::map<std::string, gz::msgs::Material> changes;
    { std::lock_guard<std::mutex> lock(this->mutex); changes.swap(this->pending); }
    if (changes.empty())
      return;
    gz::sim::SdfEntityCreator creator(_ecm, *this->events);
    for (const auto &change : changes)
    {
      gz::sim::Entity entity = gz::sim::kNullEntity;
      auto previous = this->current.find(change.first);
      if (previous != this->current.end() && _ecm.HasEntity(previous->second))
        entity = previous->second;
      else
      {
        auto entities = gz::sim::entitiesFromScopedName(change.first, _ecm);
        if (entities.size() != 1)
        {
          std::lock_guard<std::mutex> lock(this->mutex);
          this->pending.try_emplace(change.first, change.second);
          continue;
        }
        entity = *entities.begin();
      }
      auto geometry = _ecm.Component<gz::sim::components::Geometry>(entity);
      auto pose = _ecm.Component<gz::sim::components::Pose>(entity);
      auto parent = _ecm.Component<gz::sim::components::ParentEntity>(entity);
      auto name = _ecm.Component<gz::sim::components::Name>(entity);
      if (!geometry || !pose || !parent || !name ||
          !_ecm.Component<gz::sim::components::Visual>(entity))
        continue;
      sdf::Visual visual;
      // Rendering may receive creation before removal. Names must remain unique.
      visual.SetName(change.first.substr(change.first.rfind("::") + 2) +
                     "__tour_" + std::to_string(++this->serial));
      visual.SetGeom(geometry->Data());
      visual.SetRawPose(pose->Data());
      visual.SetCastShadows(false);
      visual.SetMaterial(gz::sim::convert<sdf::Material>(change.second));
      auto parentEntity = parent->Data();
      auto replacement = creator.CreateEntities(&visual);
      creator.SetParent(replacement, parentEntity);
      this->current[change.first] = replacement;
      creator.RequestRemoveEntity(entity);
    }
  }

  private: gz::sim::EventManager *events = nullptr;
  private: gz::transport::Node node;
  private: std::mutex mutex;
  private: std::map<std::string, gz::msgs::Material> pending;
  private: std::map<std::string, gz::sim::Entity> current;
  private: unsigned int serial = 0;
};
}
GZ_ADD_PLUGIN(heritage_tour::ScreenSystem, gz::sim::System,
              gz::sim::ISystemConfigure, gz::sim::ISystemPreUpdate)
GZ_ADD_PLUGIN_ALIAS(heritage_tour::ScreenSystem, "heritage_tour::ScreenSystem")
