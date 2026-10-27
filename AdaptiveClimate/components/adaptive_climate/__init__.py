"""Observation-only thermal identification. There is deliberately no output binding."""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor, binary_sensor, text_sensor
from esphome.const import CONF_ID

AUTO_LOAD = ["sensor", "text_sensor", "binary_sensor"]
MULTI_CONF = True
ns = cg.esphome_ns.namespace("adaptive_climate")
AdaptiveClimate = ns.class_("AdaptiveClimate", cg.PollingComponent)
INPUTS = ("room_temperature", "outdoor_temperature", "valve_command", "supply_temperature")
FLAGS = ("heating_active", "window_open", "dhw_active")
OUTPUTS = ("prediction_15min", "prediction_30min", "prediction_60min", "residual_rmse", "training_samples", "heating_excitation")

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(AdaptiveClimate),
    cv.Optional("mode", default="observe"): cv.one_of("observe", lower=True),
    cv.Optional("stale_after", default="15min"): cv.All(
        cv.positive_time_period_milliseconds,
        cv.Range(min=cv.TimePeriod(minutes=1), max=cv.TimePeriod(minutes=60))),
    **{cv.Required(key): cv.use_id(sensor.Sensor) for key in INPUTS},
    **{cv.Required(key): cv.use_id(binary_sensor.BinarySensor) for key in FLAGS},
    **{cv.Optional(key): sensor.sensor_schema(
        accuracy_decimals=0 if key == "training_samples" else 3,
        unit_of_measurement="°C" if key.startswith("prediction") or key == "residual_rmse" else "",
        entity_category="diagnostic",
    ) for key in OUTPUTS},
    cv.Optional("status"): text_sensor.text_sensor_schema(entity_category="diagnostic"),
}).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_stale_after(config["stale_after"].total_milliseconds))
    for index, key in enumerate(INPUTS):
        cg.add(var.set_input(index, await cg.get_variable(config[key])))
    for index, key in enumerate(FLAGS):
        cg.add(var.set_flag(index, await cg.get_variable(config[key])))
    for index, key in enumerate(OUTPUTS):
        if key in config:
            cg.add(var.set_diagnostic(index, await sensor.new_sensor(config[key])))
    if "status" in config:
        cg.add(var.set_status(await text_sensor.new_text_sensor(config["status"])))
