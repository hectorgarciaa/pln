"""Excepciones de dominio para la aplicación."""


class QuijoteIRError(Exception):
    """Excepción base del proyecto."""


class ConfigurationError(QuijoteIRError):
    """Se lanza cuando falta configuración o dependencias de entorno."""


class ArtifactMissingError(QuijoteIRError):
    """Se lanza cuando falta un artefacto preprocesado obligatorio."""


class ResourceOutOfDateError(QuijoteIRError):
    """Se lanza cuando un artefacto existe pero está desactualizado."""


class SemanticModelError(QuijoteIRError):
    """Se lanza cuando la búsqueda semántica no puede usar el modelo vectorial requerido."""
